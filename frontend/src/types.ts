/** 共享类型。从 useWebSocket.ts 提取，供多个组件使用。 */

// ── 服务端消息（JSON-RPC 2.0 Notification） ──────────────────────

export interface ThinkingMessage {
  jsonrpc: "2.0"
  method: "window/thinking"
  params: { token: string }
}

export interface DeltaMessage {
  jsonrpc: "2.0"
  method: "window/delta"
  params: { token: string }
}

export interface FlushMessage {
  jsonrpc: "2.0"
  method: "window/flush"
  params: Record<string, never>
}

export interface DisplayMessage {
  jsonrpc: "2.0"
  method: "window/display"
  params: { content: string }
}

export interface UserMessage {
  jsonrpc: "2.0"
  method: "window/user"
  params: { content: string }
}

export type ServerMessage =
  | ThinkingMessage
  | DeltaMessage
  | FlushMessage
  | DisplayMessage
  | UserMessage

// ── 渲染用消息 ────────────────────────────────────────

export interface RenderedMessage {
  id: string
  role: "user" | "assistant" | "thinking" | "system"
  content: string
}