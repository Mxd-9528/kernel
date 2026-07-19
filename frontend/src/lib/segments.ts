/**
 * Contract: 按 <EXEC>+``` 组合标记把消息文本切成有序段列表。
 *
 * 只有 <EXEC> 后紧跟（可跳过空白）``` 才算真正的可执行块开始；
 * 孤立的 <EXEC> 当普通文本。
 *
 * 用途：
 *   1. 流式判断——真正的 exec 段（含未闭合）应被隐藏（"攒着"），
 *      文本段和孤立 <EXEC> 可即时打字机显示。
 *   2. 渲染分派——文本段走 markdown，已闭合 exec 段走可折叠 CodeBlock，
 *      未闭合 exec 段走 markdown 文本。
 *
 * 承诺：
 *   - 所有段 content 拼接 = 原文抹去 <EXEC>+``` / ```+</EXEC> 标记后的结果
 *   - 至多一个 closed=false 段，若存在必为末尾
 *   - 相邻段类型不同
 *   - 空字符串返回 []
 */

export type Segment =
  | { type: "text"; content: string }
  | { type: "exec"; content: string; closed: boolean }

const OPEN = "<EXEC>"
const _OPEN_RE = /<EXEC>\s*```(\w+)?\n?/
const _CLOSE_RE = /```\s*<\/EXEC>/

export function splitByExec(text: string): Segment[] {
  if (!text) return []

  const segments: Segment[] = []
  let i = 0

  while (i < text.length) {
    // 找真实开标记（<EXEC> 后紧跟 ```）
    const m = text.slice(i).match(_OPEN_RE)
    if (!m) {
      pushText(segments, text.slice(i))
      break
    }
    const openStart = i + (m.index ?? 0)
    if (openStart > i) pushText(segments, text.slice(i, openStart))

    const contentStart = openStart + m[0].length  // 跳过 <EXEC>\s*```

    // 找闭合标记（```\s*</EXEC>）
    const rest = text.slice(contentStart)
    const closeM = rest.match(_CLOSE_RE)
    if (!closeM) {
      // 未闭合 → closed=false
      segments.push({ type: "exec", content: rest, closed: false })
      break
    }
    const code = rest.slice(0, closeM.index ?? 0).trimEnd()
    segments.push({ type: "exec", content: code, closed: true })
    i = contentStart + (closeM.index ?? 0) + closeM[0].length
  }

  return segments
}

function pushText(segs: Segment[], content: string): void {
  if (!content) return
  const last = segs[segs.length - 1]
  if (last && last.type === "text") {
    last.content += content
  } else {
    segs.push({ type: "text", content })
  }
}

/**
 * 可见前缀：把 buffer 中未闭合 EXEC 段之前的部分拼回文本（含已闭合的 EXEC 段完整保留）。
 * 用于流式期间从 buffer 派生 pending 消息的 content。
 * 额外切掉末尾 <EXEC> 标签的任何部分前缀（"<", "<E", ..., "<EXEC"），
 * 避免逐字符打字机把标签字符漏出屏幕。
 */
export function visiblePrefix(buffer: string): string {
  const segs = splitByExec(buffer)
  const parts: string[] = []
  for (const s of segs) {
    if (s.type === "exec" && !s.closed) break
    if (s.type === "exec") parts.push(rebuildExec(s.content))
    else parts.push(s.content)
  }
  return stripTrailingOpenPrefix(parts.join(""))
}

function stripTrailingOpenPrefix(text: string): string {
  for (let n = OPEN.length - 1; n >= 1; n--) {
    if (text.endsWith(OPEN.slice(0, n))) return text.slice(0, -n)
  }
  return text
}

/** 从 exec 段内容重建可见文本（含标记），用于 visiblePrefix。 */
function rebuildExec(content: string): string {
  return `<EXEC>\n\`\`\`\n${content}\n\`\`\`</EXEC>`
}

/** buffer 中是否存在未闭合 exec 段（决定是否显示 StreamingIndicator）。 */
export function hasPendingExec(buffer: string): boolean {
  const segs = splitByExec(buffer)
  if (segs.length === 0) return false
  const last = segs[segs.length - 1]
  return last.type === "exec" && !last.closed
}
