/**
 * Contract: WebSocket 连接生命周期管理。
 *
 * 隐藏：重连、JSON 解析、消息缓冲、连接状态机。
 * 暴露：{ status, messages, send } 三个接口。
 *
 * 对应后端 observer.py 的 5 种消息类型：
 *   thinking → 模型思考 token
 *   delta    → 模型输出 token
 *   flush    → 一轮输出结束，渲染 markdown
 *   display  → 系统消息（命令反馈等）
 *   user     → 用户输入回显（一等事件，刷新后 history 回放不丢失）
 */

import { useState, useEffect, useRef, useCallback } from "react"
import type { ServerMessage, RenderedMessage } from "../types"

// ── 纯函数：消息聚合状态机 ──────────────────────────────

export interface BufferState {
  messages: RenderedMessage[]
  buffer: string
  bufferType: "thinking" | "delta" | null
  tokenCount: number
}

// ponytail: crypto.randomUUID() 是浏览器原生 API，不用手写计数器

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
            {
              id: crypto.randomUUID(),
              role: "thinking",
              content: state.buffer,
            },
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

  const send = useCallback(
    (text: string) => {
      wsRef.current?.send(JSON.stringify({ jsonrpc: "2.0", method: "chat/send", params: { text } }))
    },
    [],
  )

  const interrupt = useCallback(
    () => {
      wsRef.current?.send(JSON.stringify({ jsonrpc: "2.0", method: "chat/interrupt", params: {} }))
    },
    [],
  )

  return { status, messages: bufferState.messages, streaming: bufferState.bufferType ? { phase: bufferState.bufferType, tokenCount: bufferState.tokenCount } : null, send, interrupt }
}