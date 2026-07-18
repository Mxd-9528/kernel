/**
 * 消息聚合状态机：纯函数 reducer + 投影。
 *
 * 模式：Reducer（reduceServerMessage）+ Projection（pendingMessage 从 buffer 派生）
 *      + State Machine（bufferType 三态：thinking / delta / null）。
 *
 * 对应后端 observer.py 的 5 种 JSON-RPC 通知：
 *   window/thinking → 模型思考 token
 *   window/delta    → 模型输出 token
 *   window/flush    → 一轮输出结束
 *   window/display  → 系统消息（命令反馈等）
 *   window/user     → 用户输入回显（一等事件，刷新后 history 回放不丢失）
 */

import type { ServerMessage, RenderedMessage } from "../../types"
import { visiblePrefix } from "../../lib/segments"

export interface BufferState {
  messages: RenderedMessage[]  // 已定型消息（不含 pending）
  buffer: string
  bufferType: "thinking" | "delta" | null
  tokenCount: number
}

const PENDING_ID = "__pending__"

export function reduceServerMessage(
  state: BufferState,
  msg: ServerMessage,
): BufferState {
  switch (msg.method) {
    case "window/thinking":
      return {
        ...state,
        buffer: state.buffer + msg.params.token,
        bufferType: "thinking",
        tokenCount: state.tokenCount + 1,
      }
    case "window/delta":
      // 从 thinking 切换到 delta：先产出 thinking 消息
      if (state.bufferType === "thinking" && state.buffer) {
        return {
          messages: [
            ...state.messages,
            { id: crypto.randomUUID(), role: "thinking", content: state.buffer },
          ],
          buffer: msg.params.token,
          bufferType: "delta",
          tokenCount: 1,
        }
      }
      return {
        ...state,
        buffer: state.buffer + msg.params.token,
        bufferType: "delta",
        tokenCount: state.tokenCount + 1,
      }
    case "window/flush": {
      if (!state.buffer) return state
      return {
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: state.bufferType === "thinking" ? "thinking" : "assistant",
            content: state.buffer,
          },
        ],
        buffer: "",
        bufferType: null,
        tokenCount: 0,
      }
    }
    case "window/display":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: crypto.randomUUID(), role: "system", content: msg.params.content },
        ],
      }
    case "window/user":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: crypto.randomUUID(), role: "user", content: msg.params.content },
        ],
      }
  }
}

/**
 * 从 buffer 派生 pending 消息（投影，无独立生命周期）。
 * 仅 delta（assistant 正文）派生 pending——按 visiblePrefix 隐藏未闭合 EXEC。
 * thinking 期间返回 null：思考内容不流式展示，flush 后作为完整消息进入历史。
 * "正在思考"的反馈由 streaming 指示器承担，与思考内容本身分离。
 *
 * displayedChars: 逐字符打字机的显示位置（buffer 前缀长度）。
 * 不传时用完整 buffer——保留原语义，供无速率控制的场景使用。
 */
export function pendingMessage(
  state: BufferState,
  displayedChars?: number,
): RenderedMessage | null {
  if (!state.buffer || state.bufferType !== "delta") return null
  const n = displayedChars ?? state.buffer.length
  const displayed = state.buffer.slice(0, n)
  const content = visiblePrefix(displayed)
  if (!content) return null
  return { id: PENDING_ID, role: "assistant", content }
}
