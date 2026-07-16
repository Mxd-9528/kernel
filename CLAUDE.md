# CLAUDE.md

项目概述见 [README.md](README.md)；设计原则见 [PRINCIPLES.md](PRINCIPLES.md)。

## 架构骨架

核心是 `agent.py` 的决策-执行-观察循环。每次会话是一个持久 Python 进程——模型定义的变量、导入的模块、写的函数跨轮保留，直到进程退出。

```
用户输入 → agent() → LLM 流式回复 → 提取 <EXEC> 块 → 执行 → 反馈 → LLM → ... → 纯文本回复（终止）
```

agent() 每轮最多 20 次迭代（`max_iters` 参数）。Ctrl+C 通过 stop_event 优雅中断。

```
while True:                     # 决策-执行-观察 循环
    before_send  → compact      # 上下文压缩
    stream_model → display      # 模型输出 + 流式渲染
    has_code()?  → 终止         # 纯文本 = 停止
    execute_code → runtime      # 代码执行
    save         → history      # 持久化
```

斜杠命令由 `commands.handle()` 直接处理，在 `chat.py` 的外层循环中触发，不经过 agent 循环。

## Observer 协议

agent 循环通过 `observer` 参数在 6 个关键节点通知外部。main.py 通过 `CompositeObserver([spinner, compact_observer, history_observer])` 显式组合，`--web` 模式额外加入 `WebSocketObserver`。agent() 默认 `BaseObserver()`（静默），调用者按需注入。

| 方法 | 触发时机 | 消费者 |
|------|----------|--------|
| `on_thinking(token)` | 收到 reasoning token | display 更新思考中 spinner |
| `on_delta(token)` | 收到正文 token | display 更新回复中 spinner |
| `on_flush()` | 流结束 | display 一次性渲染累积正文 |
| `before_send(messages, model)` | 发 LLM 请求前 | compact 压缩上下文 |
| `save(messages)` | 消息列表变更 | history 存盘 |
| `display_msg(content)` | 显示命令结果等非流式消息 | display 输出 |

## 注入机制

`inject.py` 只在首次执行时把机件（agent、chat、compact 等）和 `tools/` 下的预置函数推入 IPython 的 `user_ns`。哨兵 `_kernel_injected` 防止重复注入——保证模型在会话中重绑定预置函数后不会被覆盖。

## 系统提示词组装

`system.py` 的 `build_system()` 按固定顺序拼接：prompt.md → 预置函数清单（扫描 tools/ 的签名+docstring） → 技能清单（扫描 skills/ 的 YAML frontmatter） → 可选的 system_append.md。

## 不读代码就不知道的

- 预置函数是预加载进 IPython `user_ns` 的普通 Python 函数，**不是** function calling 工具。
- `tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动发现，新增能力仅需创建文件，无需注册。
- Python 标准库一行代码可完成的操作不封装为预置函数。
- 前端开发阶段 Vite 代理 `/ws` 到 `localhost:8765`，零后端改动。构建时 `vite.config.ts` 的 `outDir` 自动输出到 `src/kernel/web/static/`，`server.py` 静态伺服无需修改。
- 前端测试在 `frontend/tests/`（非项目根 `tests/`），因为 Vite 模块解析要求测试在 Vite 根目录内。

## 配置

项目配置文件在项目根目录下：
- `models.json`：LLM 模型列表，JSON 数组，每项含 url/key_env/model，首个为默认
- `.env`：API key 等环境变量（setdefault 不覆盖已有）
- `history.json`：对话历史持久化文件（.gitignore 排除）
- `prompt.md`：系统提示词主体（在 `src/kernel/` 内）
- `compact_prompt.md`：上下文压缩用提示词（在 `src/kernel/` 内）
- `system_append.md`：可选，拼在系统提示词末尾（在 `src/kernel/` 内）

## 命令

```bash
make install    # 一键安装所有依赖（Python + 前端）
make test       # 跑全部测试（Python + 前端）
make build      # 前端构建到 static/
make lint       # 代码检查（Python + 前端）

# Python
pip install -e .            # 安装 Python 依赖
ma                          # 启动对话（CLI 入口）
ma --web                    # 启动对话 + WebSocket 后端（端口 8765）
python -m pytest tests/     # 运行 Python 测试
ruff check src/ tests/      # Python 代码检查

# 前端
cd frontend && npm install  # 安装前端依赖（仅首次）
cd frontend && npm run dev  # Vite dev server（端口 5173，/ws 代理到 8765）
cd frontend && npm test     # 前端测试（vitest）
cd frontend && npx tsc -b --noEmit  # TypeScript 类型检查
```

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。命令显示通过 `display_msg` 通知输出。
