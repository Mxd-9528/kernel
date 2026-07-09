# CLAUDE.md

设计思想见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## 架构骨架

模块通过 `@on`/`emit` 事件系统（`agent.py` 全局注册表）耦合，非直接导入。注册即接入，不修改注册表。

```
事件            处理器          职责
send         ← llm.py         LLM 调用
before_send  ← compact.py     上下文压缩
execute      ← runtime.py     代码执行
on_command   ← commands.py     命令处理
```

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

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。斜杠命令由 `chat.py` 调度、`commands.py` 处理。
