# kernel/ AGENTS.md

Python 内核。持久 IPython 进程 + 决策-执行-观察循环。

## 架构骨架

`agent.py` 的循环是核心：

```
while True:
    compact.compact()  → 上下文压缩     # 纯后端逻辑
    stream_model       → display       # 模型输出 + 流式渲染
    has_code()?        → 终止          # 纯文本 = 停止
    execute_code       → runtime       # <EXEC> 块执行
    history.save()     → 持久化        # 纯后端逻辑
```

每轮最多 `max_iters=20` 次迭代。`Ctrl+C` 与 WebSocket 中断共用 `threading.Event`。
斜杠命令在 `chat.py` 外层拦截，不进入 agent 循环。

## 关键文件

| 文件 | 角色 |
|---|---|
| `agent.py` | 决策-执行-观察循环 |
| `chat.py` | 外层 REPL，处理斜杠命令 |
| `main.py` | CLI 入口（`ma` 命令），分叉终端/Web |
| `runtime.py` + `inject.py` | 持久 IPython 内核 + 首轮命名空间注入 |
| `system.py` | 扫 tools/ 与 skills/，组装系统提示词 |
| `llm.py` | 模型调用（流式） |
| `display.py` | 终端传输适配器：从协议队列消费 → Rich 渲染 |
| `history.py` | 消息持久化到 history.json |
| `compact.py` | 上下文压缩 |
| `observer.py` | Observer 契约 + ProtocolObserver（JSON-RPC 序列化 Port，唯一事实源） |
| `commands.py` | 斜杠命令处理 |

## 注入机制

`inject.py` 只在首次执行时把机件（agent/chat/compact/...）和 `tools/` 下的预置函数推入 IPython `user_ns`。
哨兵 `_kernel_injected` 防止重复注入——保证模型在会话中重绑定预置函数后不会被覆盖。
代价：新增 tools/ 文件需重启会话才生效。

## 系统提示词组装

`build_system()` 固定顺序拼接：

1. `prompt.md`（本目录）
2. 预置函数清单（扫描 `tools/` 的签名 + docstring）
3. 技能清单（扫描 `skills/` 的 YAML frontmatter）
4. 可选 `system_append.md`（本目录，存在则拼）

## 配置文件

项目根目录：
- `models.json` — LLM 列表，JSON 数组，首个为默认
- `.env` — API key（setdefault 不覆盖已有）
- `history.json` — 对话历史（.gitignore 排除）

本目录：
- `prompt.md` — 系统提示词主体
- `compact_prompt.md` — 压缩用提示词
- `system_append.md` — 可选，拼在末尾
