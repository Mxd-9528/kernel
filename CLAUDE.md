# CLAUDE.md

设计思想见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## 项目概述

基于持久 IPython 内核的自驱动 agent。模型输出 `<!EXEC>` 包裹的 Python 代码块，在内核中执行并将结果反馈回模型，循环至任务完成。预置函数是预加载进内核命名空间的普通 Python 函数，不是工具调用协议 (function calling) 意义上的工具。

## 命令

```bash
pip install -e .          # 安装依赖
python chat.py            # 启动对话
python tests.py           # 运行测试
uvx ruff check .          # Python 3.8 静态检查
```

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。

## 文件职责

| 文件 | 职责 |
|---|---|
| `chat.py` | 交互入口：输入循环、斜杠命令、调用 agent、持久化历史 |
| `agent.py` | 自驱动循环编排 + 流式 HTTP 调用：LLM 回复 → 提取代码块 → 执行 → 反馈 → 重复 |
| `_llm.py` | LLM 调用工具：读配置、发请求、取回复 |
| `_display.py` | Rich Live 终端渲染，纯显示 |
| `compact.py` | 上下文压缩 (触发判定、结构化摘要) |
| `inject.py` | `shell.push` 将对象推入 IPython `user_ns`，幂等 |
| `_system.py` | `tools/` 目录自动发现 + `skills/*/SKILL.md` 自动发现 + 系统提示组装 |
| `history.py` | 对话历史持久化 |
| `models.json` | LLM 端点配置；默认模型为首个键 |

## 返回值与错误传递

预置函数返回 **Python 原生类型**：`str` / `list` / `dict` / `subprocess.CompletedProcess` 等。**失败通过 `raise` 传递原生异常**（Python 惯例）——`FileNotFoundError` / `ValueError` / `subprocess.TimeoutExpired` 等。

**无自造包装类**（无 Result 三元组）——模型天然识别标准类型，无需被教。功能实现（如 `read` 加行号、`edit` 唯一匹配容错）保留在预置函数内部，是"少写几行代码 + 深思熟虑"的价值兑现；返回容器仅用 Python 标准类型。

**bash 特例**：命令退出码非零**不是异常**——`bash("exit 1")` 正常返回 `subprocess.CompletedProcess`，`.returncode == 1`。判断命令成败查 `.returncode`。

## 预置函数

`tools/` 目录，一函数一文件，`_system.py` 自动发现：`read` / `glob` / `grep` / `write` / `edit` / `bash` / `plan` / `survey` / `bg_start`。

## 技能

`skills/<name>/SKILL.md` 文件，含 YAML frontmatter；`_system.py` 扫描注册元数据；正文按需通过 `read()` 加载。

## 接口哲学

**不为单消费者设置接口层。** 接口层的价值在于隔离多处调用者与实现之间的依赖。只有一个消费者时，接口层只是多一个文件需要打开，增加认知负荷而不提供隔离收益。

`_` 前缀的模块（`_llm`、`_display`、`_runtime`、`_system`）是 PEP 8 私有命名约定，标识"内部实现细节"。它们被直接 import 是正常用法，不是封装泄漏。

仅当满足以下条件时，才考虑新增接口层（如 `call.py` 之于 `_call.py`）：
- 功能已收敛、接口稳定
- 有多个独立消费者
- 接口面积（10–25 行）远小于实现面积

## 硬约束

- **同进程单例**：修改磁盘代码后需重启 `python chat.py`。强隔离通过子进程 (`bash('python -c ...')`) 实现，不通过重置内核。
- **Python 3.8 兼容**：不使用 `dict |`、`list[int]`、`str.removeprefix` 等 3.9+ 语法。
- **约定优于配置**：`tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动接入，新增能力仅需创建文件。
- **最小预置**：Python 标准库一行代码可完成的操作不封装为预置函数。
