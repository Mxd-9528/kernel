# web/ AGENTS.md

WebSocket 服务端。终端与浏览器共用 `chat.py` 主循环，通过 Observer 分流输出。

## Observer 协议

`agent()` 在 7 个节点通知 observer。`main.py` 用 `CompositeObserver` 显式组合订阅者；
`--web` 模式额外注入 `WebSocketObserver`。

| 方法 | 触发时机 | 消费者 |
|---|---|---|
| `on_thinking(token)` | 收到 reasoning token | 思考中 spinner |
| `on_delta(token)` | 收到正文 token | 回复中 spinner |
| `on_flush()` | 流结束 | 累积正文一次性渲染 |
| `on_user(text)` | 浏览器发送用户输入 | 写入消息历史 |
| `before_send(messages, model)` | 发 LLM 请求前 | 上下文压缩 |
| `save(messages)` | 消息列表变更 | 存盘 |
| `display_msg(content)` | 非流式消息（命令结果等） | 输出 |

## JSON-RPC 消息

WebSocket 走 JSON-RPC 2.0 **Notification**（无 id，无回复）。

**出站（服务端 → 浏览器）**：
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
