/** 共享类型。从 useWebSocket.ts 提取，供多个组件使用。 */

// ── 服务端消息（对应 observer.py） ──────────────────────

export interface ThinkingMessage {
  type: "thinking"
  token: string
}

export interface DeltaMessage {
  type: "delta"
  token: string
}

export interface FlushMessage {
  type: "flush"
}

export interface DisplayMessage {
  type: "display"
  content: string
}

export type ServerMessage =
  | ThinkingMessage
  | DeltaMessage
  | FlushMessage
  | DisplayMessage

// ── 渲染用消息 ────────────────────────────────────────

export interface RenderedMessage {
  id: string
  role: "user" | "assistant" | "thinking" | "system"
  content: string
}