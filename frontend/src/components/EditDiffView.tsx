
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
  const pattern = /edit\s*\(\s*(["'])(.*?)\1\s*,\s*(["'])([\s\S]*?)\3\s*,\s*(["'])([\s\S]*?)\5\s*\)/
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

  // 简单逐行对比，标记变化行
  const oldLines = diff.oldCode.split("\n")
  const newLines = diff.newCode.split("\n")
  const maxLen = Math.max(oldLines.length, newLines.length)

  const oldResult: { line: string; changed: boolean }[] = []
  const newResult: { line: string; changed: boolean }[] = []

  for (let i = 0; i < maxLen; i++) {
    const oldLine = oldLines[i] ?? ""
    const newLine = newLines[i] ?? ""

    if (i < oldLines.length && i < newLines.length) {
      const changed = oldLine !== newLine
      if (i < oldLines.length) oldResult.push({ line: oldLine, changed })
      if (i < newLines.length) newResult.push({ line: newLine, changed })
    } else if (i < oldLines.length) {
      oldResult.push({ line: oldLine, changed: true })
    } else {
      newResult.push({ line: newLine, changed: true })
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
