# web/ AGENTS.md

WebSocket 服务端。终端与浏览器共用 `chat.py` 主循环。两者都用 `ProtocolObserver`
把显示事件序列化为 JSON-RPC dict 入队，各自的传输适配器从队列消费——协议是唯一事实源。

## Observer 协议（六边形架构）

- **Port**：`observer.ProtocolObserver` —— `agent()` 在 5 个纯显示节点调其方法，
  产 JSON-RPC dict 入 `self.messages` 队列。序列化的唯一事实源。
- **Adapter**：从队列消费 dict 的传输层。已有两个：
  - `web/observer.WebSocketObserver`（继承 `ProtocolObserver`）+ `web/server.py` → 浏览器
  - `display.TerminalRenderer`（消费 `obs.messages`）→ 终端 Rich 渲染
- 新语言/新传输前端接入：继承 `ProtocolObserver` 复用序列化 → 从队列取 dict → 写传输。

| 方法 | JSON-RPC method | 触发时机 |
|---|---|---|
| `on_thinking(token)` | `window/thinking` | 收到 reasoning token |
| `on_delta(token)` | `window/delta` | 收到正文 token |
| `on_flush(text)` | `window/flush` | 流结束，全文兜底 |
| `on_user(text)` | `window/user` | 浏览器发送用户输入 |
| `display_msg(content)` | `window/display` | 非流式消息（命令结果等） |

## JSON-RPC 消息

走 JSON-RPC 2.0 **Notification**（无 id，无回复）。

**出站（服务端 → 浏览器 / 内核 → 终端）**：
- `window/thinking` — reasoning token
- `window/delta` — 正文 token
- `window/flush` — 流结束标记
- `window/display` — 一次性消息
- `window/user` — 用户消息回显

**入站（浏览器 → 服务端）**：
- `chat/send` — 用户输入
- `chat/interrupt` — 中断当前 agent 循环（走 `threading.Event`）

## 静态资源

`server.py` 从 `web/static/` 伺服，该目录由 `cd frontend && npm run build` 生成。
`vite.config.ts` 的 `outDir` 已配置为 `../src/kernel/web/static/`，无需手动改动。
