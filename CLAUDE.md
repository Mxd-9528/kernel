# CLAUDE.md

设计思想见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## 架构骨架

核心是 `agent.py` 的决策-执行-观察循环。事件系统（`@on`/`emit`）是循环身上的钩子，非架构骨架。注册即接入，不修改注册表。

```
while True:                     # 决策-执行-观察 循环
    before_send  → compact      # 上下文压缩
    stream_model → display      # 模型输出 + 流式渲染
    has_code()?  → 终止         # 纯文本 = 停止
    execute_code → runtime      # 代码执行
    save         → history      # 持久化
```

斜杠命令通过 `on_command` 事件处理，在 `chat.py` 的外层循环中触发，不经过 agent 循环。

## 不读代码就不知道的

- 预置函数是预加载进 IPython `user_ns` 的普通 Python 函数，**不是** function calling 工具。
- `tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动发现，新增能力仅需创建文件，无需注册。
- Python 标准库一行代码可完成的操作不封装为预置函数。

## 命令

```bash
pip install -e .          # 安装依赖
python main.py            # 启动对话
python tests.py           # 运行测试
uvx ruff check .          # Python 3.10
```

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。命令显示通过 `display` 事件输出。
