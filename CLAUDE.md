# CLAUDE.md

设计思想见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## 项目概述

基于持久 IPython 内核的自驱动 agent。模型输出 `<!EXEC>` 包裹的 Python 代码块，在内核中执行并将结果反馈回模型，循环至任务完成。预置函数是预加载进内核命名空间的普通 Python 函数，不是工具调用协议 (function calling) 意义上的工具。

## 命令

```bash
pip install -e .          # 安装依赖
python chat.py            # 启动对话
python tests.py           # 运行测试
uvx ruff check .          # Python 3.10
```

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。

## 文件职责

| 文件 | 职责 |
|---|---|
| `chat.py` | 交互入口：输入循环、斜杠命令、调用 agent、持久化历史 |
| `agent.py` | 自驱动循环编排 + 流式 HTTP 调用：LLM 回复 → 提取代码块 → 执行 → 反馈 → 重复 |
| `llm.py` | LLM 调用工具：读配置、发请求、取回复 |
| `display.py` | Rich Live 终端渲染，纯显示 |
| `compact.py` | 上下文压缩 (触发判定、结构化摘要) |
| `inject.py` | `shell.push` 将对象推入 IPython `user_ns`，幂等 |
| `system.py` | `tools/` 目录自动发现 + `skills/*/SKILL.md` 自动发现 + 系统提示组装 |
| `history.py` | 对话历史持久化 |
| `models.json` | LLM 端点配置；默认模型为首个键 |

## 硬约束

- **约定优于配置**：`tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动接入，新增能力仅需创建文件。
- **最小预置**：Python 标准库一行代码可完成的操作不封装为预置函数。
