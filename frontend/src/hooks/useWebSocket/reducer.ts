/**
 * 消息聚合状态机：纯函数 reducer + 投影。
 *
 * 模式：Reducer（reduceServerMessage）+ Projection（draftMessage 从 buffer 派生）
 *      + State Machine（phase 三态：thinking / delta / null）。
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

export interface StreamState {
  messages: RenderedMessage[]  // 已定型消息（不含 draft）
  buffer: string
  phase: "thinking" | "delta" | null
  tokenCount: number
}

const DRAFT_ID = "__draft__"

export function reduceServerMessage(
  state: StreamState,
  msg: ServerMessage,
): StreamState {
  switch (msg.method) {
    case "window/thinking":
      return {
        ...state,
        buffer: state.buffer + msg.params.token,
        phase: "thinking",
        tokenCount: state.tokenCount + 1,
      }
    case "window/delta":
      // 从 thinking 切换到 delta：先产出 thinking 消息
      if (state.phase === "thinking" && state.buffer) {
        return {
          messages: [
            ...state.messages,
            { id: crypto.randomUUID(), role: "thinking", content: state.buffer },
          ],
          buffer: msg.params.token,
          phase: "delta",
          tokenCount: 1,
        }
      }
      return {
        ...state,
        buffer: state.buffer + msg.params.token,
        phase: "delta",
        tokenCount: state.tokenCount + 1,
      }
    case "window/flush": {
      if (!state.buffer) return state
      return {
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: state.phase === "thinking" ? "thinking" : "assistant",
            content: state.buffer,
          },
        ],
        buffer: "",
        phase: null,
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
 * 从 buffer 派生 draft 消息（投影，无独立生命周期）。
 * 仅 delta（assistant 正文）派生 draft——按 visiblePrefix 隐藏未闭合 EXEC。
 * thinking 期间返回 null：思考内容不流式展示，flush 后作为完整消息进入历史。
 * "正在思考"的反馈由 streaming 指示器承担，与思考内容本身分离。
 */
export function draftMessage(state: StreamState): RenderedMessage | null {
  if (!state.buffer || state.phase !== "delta") return null
  const content = visiblePrefix(state.buffer)
  if (!content) return null
  return { id: DRAFT_ID, role: "assistant", content }
}
