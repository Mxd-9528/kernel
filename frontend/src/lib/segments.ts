/**
 * Contract: 按 <EXEC>...</EXEC> 标签把消息文本切成有序段列表。
 *
 * 用途：
 *   1. 流式判断——未闭合的 EXEC 段应被隐藏（"攒着"），文本段可即时打字机显示。
 *   2. 渲染分派——文本段走 markdown，EXEC 段走可折叠 CodeBlock。
 *
 * 承诺：
 *   - 所有段 content 拼接 = 原文抹去 <EXEC>/</EXEC> 标签后的结果
 *   - 至多一个 closed=false 段，若存在必为末尾
 *   - 相邻段类型不同
 *   - 空字符串返回 []
 */

export type Segment =
  | { type: "text"; content: string }
  | { type: "exec"; content: string; closed: boolean }

const OPEN = "<EXEC>"
const CLOSE = "</EXEC>"

export function splitByExec(text: string): Segment[] {
  if (!text) return []

  const segments: Segment[] = []
  let i = 0

  while (i < text.length) {
    const openIdx = text.indexOf(OPEN, i)

    if (openIdx === -1) {
      // 剩余全是文本
      pushText(segments, text.slice(i))
      break
    }

    // openIdx 之前是文本
    if (openIdx > i) pushText(segments, text.slice(i, openIdx))

    const contentStart = openIdx + OPEN.length
    const closeIdx = text.indexOf(CLOSE, contentStart)

    if (closeIdx === -1) {
      // 未闭合 EXEC，吞掉剩余
      segments.push({ type: "exec", content: text.slice(contentStart), closed: false })
      break
    }

    segments.push({ type: "exec", content: text.slice(contentStart, closeIdx), closed: true })
    i = closeIdx + CLOSE.length
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
    if (s.type === "exec") parts.push(`<EXEC>${s.content}</EXEC>`)
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

/** buffer 中是否存在未闭合 EXEC（决定是否显示 StreamingIndicator）。 */
export function hasPendingExec(buffer: string): boolean {
  const openIdx = buffer.lastIndexOf(OPEN)
  if (openIdx === -1) return false
  const closeIdx = buffer.indexOf(CLOSE, openIdx + OPEN.length)
  return closeIdx === -1
}
