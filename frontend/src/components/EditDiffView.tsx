import { useState } from "react"
import { diffArrays, diffWordsWithSpace } from "diff"

export interface EditDiff {
  filePath: string
  oldCode: string
  newCode: string
}

// 识别锚点：edit 前是行首或非标识符字符——避免 readit( 之类误匹配
const EDIT_ANCHOR = /(?:^|[^A-Za-z0-9_.])edit\s*\(/

// 读取 Python 字符串字面量（支持 raw 前缀、triple-quoted、常见转义）
function readString(code: string, i: number): { value: string; next: number } | null {
  let j = i
  const pre = code.slice(j).match(/^[rRbBfFuU]{1,2}(?=['"])/)
  const raw = !!pre && /[rR]/.test(pre[0])
  if (pre) j += pre[0].length
  const ch = code[j]
  if (ch !== '"' && ch !== "'") return null
  const triple = code.slice(j, j + 3) === ch + ch + ch
  const quote = triple ? ch + ch + ch : ch
  j += quote.length
  const ESC: Record<string, string> = { n: "\n", t: "\t", r: "\r", "\\": "\\", "\"": "\"", "'": "'", "0": "\0" }
  let value = ""
  while (j < code.length) {
    if (code.slice(j, j + quote.length) === quote) return { value, next: j + quote.length }
    if (!raw && code[j] === "\\" && j + 1 < code.length) {
      const nxt = code[j + 1]
      value += ESC[nxt] !== undefined ? ESC[nxt] : code[j] + nxt
      j += 2
      continue
    }
    value += code[j]
    j++
  }
  return null
}

// 纯函数：从 content 解析 edit() 调用
// 分层：锚点识别 → 参数扫描（位置 + kwargs + 忽略非字符串 kwarg 如 replace_all=True）
export function parseEditCall(code: string): EditDiff | null {
  const m = code.match(EDIT_ANCHOR)
  if (!m) return null
  let i = m.index! + m[0].length
  const pos: string[] = []
  const kw: Record<string, string> = {}
  while (i < code.length) {
    while (i < code.length && /\s/.test(code[i])) i++
    if (code[i] === ")") break
    const nameM = code.slice(i).match(/^([A-Za-z_]\w*)\s*=(?!=)\s*/)
    if (nameM) {
      const after = i + nameM[0].length
      const s = readString(code, after)
      if (s) { kw[nameM[1]] = s.value; i = s.next }
      else { i = after; while (i < code.length && code[i] !== "," && code[i] !== ")") i++ }
    } else {
      const s = readString(code, i)
      if (!s) return null
      pos.push(s.value)
      i = s.next
    }
    while (i < code.length && /\s/.test(code[i])) i++
    if (code[i] === ",") i++
    else if (code[i] === ")") break
    else return null
  }
  const filePath = pos[0] ?? kw.file_path
  const oldCode = pos[1] ?? kw.old_string
  const newCode = pos[2] ?? kw.new_string
  if (filePath === undefined || oldCode === undefined || newCode === undefined) return null
  return { filePath, oldCode, newCode }
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
