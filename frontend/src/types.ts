/** 共享类型。从 useWebSocket.ts 提取，供多个组件使用。 */

// ── 服务端消息（JSON-RPC 2.0 Notification） ──────────────────────

export type ServerMessage =
  | { jsonrpc: "2.0"; method: "window/thinking"; params: { token: string } }
  | { jsonrpc: "2.0"; method: "window/delta"; params: { token: string } }
  | { jsonrpc: "2.0"; method: "window/flush"; params: { text?: string } }
  | { jsonrpc: "2.0"; method: "window/display"; params: { content: string } }
  | { jsonrpc: "2.0"; method: "window/user"; params: { content: string } }

// ── 渲染用消息 ────────────────────────────────────────

export interface RenderedMessage {
  id: string
  role: "user" | "assistant" | "thinking" | "system"
  content: string
}