import { useState } from "react"
import { diffArrays, diffWordsWithSpace } from "diff"

export interface EditDiff {
  filePath: string
  oldCode: string
  newCode: string
}

// 纯函数：从 content 解析 edit() 调用
export function parseEditCall(code: string): EditDiff | null {
  // 简单的正则，不处理复杂转义
  // 不加前缀守卫——首行是注释时也应能识别（正则自身即守卫）
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

  // 行级 diff → 双栏对齐；修改行内做词级 diff 高亮
  type Seg = { text: string; kind: "same" | "del" | "add" }
  type Row = { segs: Seg[]; changed: boolean }
  const plain = (line: string, kind: Seg["kind"]): Seg[] => [{ text: line, kind }]
  const wordPair = (o: string, n: string): [Seg[], Seg[]] => {
    if (o === "") return [plain("", "same"), plain(n, "add")]
    if (n === "") return [plain(o, "del"), plain("", "same")]
    const parts = diffWordsWithSpace(o, n)
    const oSegs: Seg[] = [], nSegs: Seg[] = []
    parts.forEach((p) => {
      if (p.added) nSegs.push({ text: p.value, kind: "add" })
      else if (p.removed) oSegs.push({ text: p.value, kind: "del" })
      else { oSegs.push({ text: p.value, kind: "same" }); nSegs.push({ text: p.value, kind: "same" }) }
    })
    return [oSegs, nSegs]
  }
  const changes = diffArrays(diff.oldCode.split("\n"), diff.newCode.split("\n"))
  const oldResult: Row[] = []
  const newResult: Row[] = []
  for (let k = 0; k < changes.length; k++) {
    const c = changes[k]
    if (!c.added && !c.removed) {
      c.value.forEach((l) => {
        oldResult.push({ segs: plain(l, "same"), changed: false })
        newResult.push({ segs: plain(l, "same"), changed: false })
      })
    } else if (c.removed && changes[k + 1]?.added) {
      const rem = c.value, add = changes[k + 1].value
      const len = Math.max(rem.length, add.length)
      for (let r = 0; r < len; r++) {
        const [oSegs, nSegs] = wordPair(rem[r] ?? "", add[r] ?? "")
        oldResult.push({ segs: oSegs, changed: true })
        newResult.push({ segs: nSegs, changed: true })
      }
      k++
    } else if (c.removed) {
      c.value.forEach((l) => {
        oldResult.push({ segs: plain(l, "del"), changed: true })
        newResult.push({ segs: plain("", "same"), changed: true })
      })
    } else {
      c.value.forEach((l) => {
        oldResult.push({ segs: plain("", "same"), changed: true })
        newResult.push({ segs: plain(l, "add"), changed: true })
      })
    }
  }
  const renderSegs = (segs: Seg[]) => segs.map((s, i) => (
    <span key={i} className={s.kind === "del" ? "edit-word-del" : s.kind === "add" ? "edit-word-add" : ""}>{s.text}</span>
  ))

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
                <div key={i} className={l.changed ? "edit-line-del" : ""}>{renderSegs(l.segs)}</div>
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
                <div key={i} className={l.changed ? "edit-line-add" : ""}>{renderSegs(l.segs)}</div>
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
