/**
 * Contract: WebSocket 连接生命周期管理 + 消息聚合状态机。
 *
 * 隐藏：重连、JSON 解析、消息缓冲、连接状态机、pending 消息投影。
 * 暴露：{ status, messages, streaming, send, interrupt }。
 *
 * 对应后端 observer.py 的 5 种 JSON-RPC 通知：
 *   window/thinking → 模型思考 token
 *   window/delta    → 模型输出 token
 *   window/flush    → 一轮输出结束
 *   window/display  → 系统消息（命令反馈等）
 *   window/user     → 用户输入回显（一等事件，刷新后 history 回放不丢失）
 *
 * 流式打字机：
 *   messages = 已 flush 消息 + pending 消息（从 buffer 派生的投影）
 *   pending 仅在 delta 期间派生——按 visiblePrefix 隐藏未闭合 EXEC 段
 *   thinking 期间不派生 pending——思考内容不流式展示，flush 后作为完整消息进历史
 *   streaming 指示器仅在 thinking 或 buffer 有未闭合 EXEC 时显示
 */

import { useState, useEffect, useRef, useCallback } from "react"
import type { ServerMessage, RenderedMessage } from "../types"
import { visiblePrefix, hasPendingExec } from "../lib/segments"

// ── 纯函数：消息聚合状态机 ──────────────────────────────

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

// ── Hook 接口 ─────────────────────────────────────────

export interface StreamingState {
  phase: "thinking" | "delta"
  tokenCount: number
}

export interface UseWebSocketReturn {
  status: "connecting" | "connected" | "disconnected"
  messages: RenderedMessage[]
  streaming: StreamingState | null
  send: (text: string) => void
  interrupt: () => void
}

// 打字机节奏：目标 TICK_MS * TARGET_TICKS ≈ 500ms 内追平任意 backlog。
const TICK_MS = 16
const TARGET_TICKS = 30

export function useWebSocket(url: string): UseWebSocketReturn {
  const [status, setStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting")
  const [bufferState, setBufferState] = useState<BufferState>({
    messages: [],
    buffer: "",
    bufferType: null,
    tokenCount: 0,
  })
  const [displayedChars, setDisplayedChars] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setStatus("connected")
    ws.onclose = () => setStatus("disconnected")
    ws.onmessage = (e) => {
      const msg: ServerMessage = JSON.parse(e.data)
      setBufferState((prev) => reduceServerMessage(prev, msg))
    }

    return () => ws.close()
  }, [url])

  // 打字机追赶：仅在 delta 期间运行；buffer 变短或 bufferType 变化时重置。
  useEffect(() => {
    if (bufferState.bufferType !== "delta") {
      if (displayedChars !== 0) setDisplayedChars(0)
      return
    }
    if (displayedChars >= bufferState.buffer.length) return
    const backlog = bufferState.buffer.length - displayedChars
    const step = Math.max(1, Math.ceil(backlog / TARGET_TICKS))
    const timer = setTimeout(() => {
      setDisplayedChars((prev) =>
        Math.min(prev + step, bufferState.buffer.length),
      )
    }, TICK_MS)
    return () => clearTimeout(timer)
  }, [bufferState.buffer, bufferState.bufferType, displayedChars])

  const send = useCallback((text: string) => {
    wsRef.current?.send(
      JSON.stringify({ jsonrpc: "2.0", method: "chat/send", params: { text } }),
    )
  }, [])

  const interrupt = useCallback(() => {
    wsRef.current?.send(
      JSON.stringify({ jsonrpc: "2.0", method: "chat/interrupt", params: {} }),
    )
  }, [])

  const pending = pendingMessage(bufferState, displayedChars)
  const messages = pending
    ? [...bufferState.messages, pending]
    : bufferState.messages

  const showStreaming =
    bufferState.bufferType === "thinking" ||
    (bufferState.bufferType === "delta" && hasPendingExec(bufferState.buffer))

  const streaming: StreamingState | null = showStreaming
    ? { phase: bufferState.bufferType!, tokenCount: bufferState.tokenCount }
    : null

  return { status, messages, streaming, send, interrupt }
}
