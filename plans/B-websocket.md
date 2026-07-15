# 方案 B：WebSocket + Web 前端

**状态：✅ 当前目标**

## 思路

observer 协议产生的事件流通过 WebSocket 发送到浏览器前端。前端用 HTML/CSS/JS 渲染——Markdown 用 marked.js，代码高亮用 highlight.js，流式文本用原生 DOM 增量更新，输入框用 `<textarea>`。所有终端渲染问题消失，因为不渲染到终端了。

## 架构图

```
                    observer 协议
agent.py ────────────────────────────→ CompositeObserver
                                            │
                                            ├── WebSocketObserver  ← 新增
                                            │       │
                                            │       └──→ WebSocket ──→ 前端 (HTML/JS)
                                            │              ↑
                                            │              └── 用户输入
                                            │
                                            ├── _CompactObserver (不变)
                                            └── _HistoryObserver (不变)
```

## 核心改动

### 新增文件

**`websocket_observer.py`** — 实现 Observer 协议，把事件序列化并通过 WebSocket 发送：

```python
class WebSocketObserver(BaseObserver):
    def on_thinking(self, token):
        self._send({"type": "thinking", "token": token})
    def on_delta(self, token):
        self._send({"type": "delta", "token": token})
    def on_flush(self):
        self._send({"type": "flush"})
    # ...
```

**`frontend.html`** — 单文件 Web 前端。三个区域：
- 消息列表（流式追加、Markdown 渲染、代码块语法高亮、`<EXEC>` 折叠）
- 输入框（`<textarea>`，支持多行，Ctrl+Enter 发送）
- 状态栏（模型名、token 计数、连接状态）

### 修改文件

**`main.py`** — 增加 `--mode` 参数，在终端和 Web 之间切换：

```python
# 终端模式（不变）
observer = CompositeObserver([spinner, compact_observer, history_observer])

# Web 模式
ws_observer = WebSocketObserver(port=8765)
observer = CompositeObserver([ws_observer, compact_observer, history_observer])
```

**`chat.py`** — Web 模式下，输入从 WebSocket 接收而非 `input()`：

```python
def chat(model=None, *, observer=None, input_source=None):
    # input_source: None 时用 input()，否则从 WebSocket 队列取
```

## observer 协议映射

| observer 方法 | WebSocket 消息 | 前端行为 |
|-------------|---------------|---------|
| `on_thinking(token)` | `{"type":"thinking","token":"..."}` | spinner 计数更新 |
| `on_delta(token)` | `{"type":"delta","token":"..."}` | 追加到当前消息块 |
| `on_flush()` | `{"type":"flush"}` | 停止 spinner，渲染完整 Markdown |
| `before_send(messages, model)` | — | （压缩在服务端完成，不通知前端） |
| `save(messages)` | — | （持久化在服务端完成，不通知前端） |
| `display_msg(content)` | `{"type":"display","content":"..."}` | 追加系统消息 |
| 用户输入 | `{"type":"input","text":"..."}` | 用户按 Ctrl+Enter 发送 |

## 前端技术选型

**零依赖原则**：一个 HTML 文件，内联 CSS 和 JS。不需要 npm、不需要构建工具、不需要框架。

- Markdown 渲染：marked.js（CDN 加载，<50KB）
- 代码高亮：highlight.js（CDN 加载，核心 ~30KB）
- WebSocket：浏览器原生 API
- 布局：CSS Grid，三区域（消息/输入/状态栏）
- 主题：暗色，CSS 变量，易于切换

## 双模式并存

不改动现有终端模式。用户通过命令行参数选择：

```bash
ma              # 终端模式（默认，不变）
ma --web        # 启动 Web 前端，浏览器自动打开
ma --web 3000   # 指定端口
```

VS Code 用户：终端模式继续在 VS Code 内置终端中使用。Web 模式可以在 VS Code 的 Simple Browser 面板中打开，或者在外部浏览器中使用。

## 关于 VS Code 使用场景的解答

### Git 版本管理

Web 前端不替代 VS Code 的 Git 面板。你仍然在 VS Code 中管理 Git——commit、push、diff、分支切换。Web 前端只是一个对话窗口，agent 修改的文件在你 VS Code 的文件树中实时可见。Workflow 不变：

1. 在 Web 前端和 agent 对话，agent 修改代码文件
2. 切回 VS Code，在 Source Control 面板中查看 diff
3. 正常 commit

### 文件操作便捷性

Web 前端不替代文件浏览器。它是对话界面，不是 IDE。文件操作（新建、重命名、删除、拖拽）在 VS Code 中完成。agent 修改文件后，VS Code 的文件树自动刷新。这是"关注点分离"——对话用对话界面，编码用 IDE。

### 前端在 VS Code 中的位置

VS Code 的 Simple Browser 面板（`> Simple Browser: Show`）可以在编辑器区域内打开一个网页。Web 前端在这个面板中运行，和终端、编辑器、文件树并存。布局示例：

```
┌──────────────┬──────────────────────────┐
│ 文件树       │ 编辑器 (agent 修改的文件) │
│              │                          │
│              ├──────────────────────────┤
│              │ Web 前端 (对话界面)       │
│              │                          │
└──────────────┴──────────────────────────┘
```

## 实施步骤

1. **Phase 1**：`websocket_observer.py` + `main.py` 增加 `--web` 参数 + 最小 HTML 前端（纯文本，无 Markdown 渲染）
2. **Phase 2**：前端增加 Markdown 渲染 + 代码高亮 + `<EXEC>` 折叠
3. **Phase 3**：前端增加会话管理（/new、/model 切换、历史浏览）
4. **Phase 4**：样式优化、主题切换、响应式布局
