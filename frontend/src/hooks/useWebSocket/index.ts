/**
 * Contract: WebSocket 连接生命周期管理 + 消息聚合状态机。
 *
 * 模式：Reducer + Projection（见 ./reducer）
 *      + State Machine（phase 三态）+ Exponential Backoff 重连（500ms→5s）。
 *
 * 隐藏：重连、JSON 解析、消息缓冲、连接状态机、draft 消息投影。
 * 暴露：{ status, messages, streaming, send, interrupt }。
 *
 * 流式渲染：
 *   messages = 已 flush 消息 + draft 消息（从 buffer 派生的投影）
 *   draft 仅在 delta 期间派生——按 visiblePrefix 隐藏未闭合 EXEC 段
 *   thinking 期间不派生 draft——思考内容不流式展示，flush 后作为完整消息进历史
 *   streaming 指示器仅在 thinking 或 buffer 有未闭合 EXEC 时显示
 */

import { useState, useEffect, useRef, useCallback } from "react"
import type { ServerMessage, RenderedMessage } from "../../types"
import { hasPendingExec } from "../../lib/segments"
import { reduceServerMessage, draftMessage, type StreamState } from "./reducer"

export { reduceServerMessage, draftMessage, type StreamState } from "./reducer"

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

export function useWebSocket(url: string): UseWebSocketReturn {
  const [status, setStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting")
  const [state, setState] = useState<StreamState>({
    messages: [],
    buffer: "",
    phase: null,
    tokenCount: 0,
  })
  const wsRef = useRef<WebSocket | null>(null)
  const disposedRef = useRef(false)

  useEffect(() => {
    disposedRef.current = false
    let retries = 0
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (disposedRef.current) return
      setStatus("connecting")
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        retries = 0
        setStatus("connected")
      }
      ws.onclose = () => {
        setStatus("disconnected")
        if (disposedRef.current) return
        const delay = Math.min(500 * Math.pow(2, retries), 5000)
        retries++
        reconnectTimer = setTimeout(connect, delay)
      }
      ws.onmessage = (e) => {
        try {
          const msg: ServerMessage = JSON.parse(e.data)
          setState((prev) => reduceServerMessage(prev, msg))
        } catch (err) {
          console.error("WS message parse failed:", err, e.data)
        }
      }
    }

    connect()

    return () => {
      disposedRef.current = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      wsRef.current?.close()
    }
  }, [url])

  const send = useCallback((text: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(
      JSON.stringify({ jsonrpc: "2.0", method: "chat/send", params: { text } }),
    )
  }, [])

  const interrupt = useCallback(() => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(
      JSON.stringify({ jsonrpc: "2.0", method: "chat/interrupt", params: {} }),
    )
  }, [])

  const draft = draftMessage(state)
  const messages = draft
    ? [...state.messages, draft]
    : state.messages

  const showStreaming =
    state.phase === "thinking" ||
    (state.phase === "delta" && hasPendingExec(state.buffer))

  const streaming: StreamingState | null = showStreaming
    ? { phase: state.phase!, tokenCount: state.tokenCount }
    : null

  return { status, messages, streaming, send, interrupt }
}
