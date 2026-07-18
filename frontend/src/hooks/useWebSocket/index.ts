/**
 * Contract: WebSocket 连接生命周期管理 + 消息聚合状态机。
 *
 * 模式：Reducer + Projection（见 ./reducer）
 *      + State Machine（bufferType 三态）+ Backpressure（TICK_MS / TARGET_TICKS 追平）。
 *
 * 隐藏：重连、JSON 解析、消息缓冲、连接状态机、pending 消息投影。
 * 暴露：{ status, messages, streaming, send, interrupt }。
 *
 * 流式打字机：
 *   messages = 已 flush 消息 + pending 消息（从 buffer 派生的投影）
 *   pending 仅在 delta 期间派生——按 visiblePrefix 隐藏未闭合 EXEC 段
 *   thinking 期间不派生 pending——思考内容不流式展示，flush 后作为完整消息进历史
 *   streaming 指示器仅在 thinking 或 buffer 有未闭合 EXEC 时显示
 */

import { useState, useEffect, useRef, useCallback } from "react"
import type { ServerMessage, RenderedMessage } from "../../types"
import { hasPendingExec } from "../../lib/segments"
import { reduceServerMessage, pendingMessage, type BufferState } from "./reducer"

export { reduceServerMessage, pendingMessage, type BufferState } from "./reducer"

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
