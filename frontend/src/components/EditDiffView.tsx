
import { useState } from "react"

export interface EditDiff {
  filePath: string
  oldCode: string
  newCode: string
}

// 纯函数：从 content 解析 edit() 调用
export function parseEditCall(code: string): EditDiff | null {
  // 先检查是不是 edit 调用
  const trimmed = code.trimStart()
  if (!trimmed.startsWith('edit(')) return null

  // 简单的正则，不处理复杂转义
  const pattern = /edit\s*\(\s*(["'])(.*?)\1\s*,\s*(["'])([\s\S]*?)\3\s*,\s*(["'])([\s\S]*?)\5\s*,?\s*\)/
  const match = code.match(pattern)
  if (!match) return null

  return {
    filePath: match[2],
    oldCode: match[4],
    newCode: match[6],
  }
}

const PREVIEW_LINES = 3

interface Props {
  code: string
  diff: EditDiff
}

export function EditDiffView({ code, diff }: Props) {
  const [open, setOpen] = useState(false)

  const lines = code.split("\n")
  const preview = lines.slice(0, PREVIEW_LINES).join("\n")
  const hasMore = lines.length > PREVIEW_LINES

  // LCS 算法：计算最长公共子序列，避免插入/删除导致的错位
  const oldLines = diff.oldCode.split("\n")
  const newLines = diff.newCode.split("\n")

  // 构建 LCS 表
  const m = oldLines.length
  const n = newLines.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // 回溯 LCS，生成对齐后的左右结果
  const oldResult: { line: string; changed: boolean }[] = []
  const newResult: { line: string; changed: boolean }[] = []
  let i = m, j = n
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      oldResult.unshift({ line: oldLines[i - 1], changed: false })
      newResult.unshift({ line: newLines[j - 1], changed: false })
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      // 新增行：右边有，左边补空行
      oldResult.unshift({ line: "", changed: true })
      newResult.unshift({ line: newLines[j - 1], changed: true })
      j--
    } else {
      // 删除行：左边有，右边补空行
      oldResult.unshift({ line: oldLines[i - 1], changed: true })
      newResult.unshift({ line: "", changed: true })
      i--
    }
  }

  return (
    <div className="code-block" onClick={() => setOpen(!open)}>
      {open ? (
        <div className="edit-diff-split">
          <div className="edit-diff-old">
            <pre style={{
              margin: 0, padding: "6px 10px", fontFamily: "JetBrains Mono, Fira Code, monospace",
              fontSize: 13, lineHeight: 1.3, overflowX: "auto", color: "var(--color-ink)",
              whiteSpace: "pre",
            }}>
              {oldResult.map((l, i) => (
                <div key={i} className={l.changed ? "edit-line-del" : ""}>{l.line}</div>
              ))}
            </pre>
          </div>
          <div className="edit-diff-new">
            <pre style={{
              margin: 0, padding: "6px 10px", fontFamily: "JetBrains Mono, Fira Code, monospace",
              fontSize: 13, lineHeight: 1.3, overflowX: "auto", color: "var(--color-ink)",
              whiteSpace: "pre",
            }}>
              {newResult.map((l, i) => (
                <div key={i} className={l.changed ? "edit-line-add" : ""}>{l.line}</div>
              ))}
            </pre>
          </div>
        </div>
      ) : (
        <pre className="code-block-preview">
          <code>{preview}{hasMore ? "\n..." : ""}</code>
        </pre>
      )}
    </div>
  )
}
