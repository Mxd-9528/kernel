# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 项目设计哲学见 [CONTEXT.md](CONTEXT.md)；给人类看的入门见 [README.md](README.md)。

## What this project is

持久 IPython 内核上的极简自驱动 agent。模型通过写 `<!EXEC>` Python 代码块来感知和改变环境，在 agent 循环中迭代直到任务完成。

**不是工具调用范式**——预置函数只是预加载进内核命名空间的普通 Python 函数，模型拿来就用，不够用直接写标准库。

## 命令速查

```bash
pip install -e .          # 装依赖
python chat.py            # 启动对话
python tests.py           # 跑全部测试
python tests_tools.py     # 只跑工具测试
uvx ruff check .          # 静态检查（py38 目标）
```

对话内：`exit` 退出，`/new` 清历史，`/model <名>` 切换模型。

## 文件职责

| 文件 | 职责 |
|---|---|
| `chat.py` | 交互入口：读输入、斜杠命令、调 agent、存/读历史 |
| `agent.py` | 自驱动循环：调 LLM → 执行代码块 → 拼反馈 → 重复直到模型回纯文本 |
| `call.py` | OpenAI 兼容 REST 调用，urllib.request 无 SDK |
| `extract.py` | 从回复中抠出 `<!EXEC>` 代码块 |
| `run.py` | 在持久 IPython 单例中执行代码，铸成三元组 Result |
| `result.py` | `Result` / `ListResult` / `DictResult`：Body + `.error` + `.facts` |
| `inject.py` | 把机件+预置函数推入内核 user_ns（`shell.push`），idempotent |
| `load.py` | 机件注入锚点：加一行 import → dir 扫描自动注入内核（同构发现模式之一） |
| `manifest.py` | 工具自动发现：`tools/` 放文件 → 自动注入+生成 prompt 文档（同构发现模式之二） |
| `skills.py` | 技能自动发现：建目录放 SKILL.md → 自动索引进 prompt（同构发现模式之三） |
| `history.py` | 对话持久化到 `history.json`，启动自动接续 |
| `compact.py` | 上下文压缩：超阈值时摘要中间历史，保留 system + 最近 6 轮 |
| `models.json` | LLM 端点配置（url / key_env / model），默认 = 文件第一个 |

## 关键约束（速记版，完整推理见 CONTEXT.md）

**架构核心哲学**：三个同构的约定驱动发现层 —— load.py（机件）、manifest.py（工具）、skills.py（技能）。统一模式：最小接口（加一行 import / 放文件 / 建目录）获得最大杠杆（注册/注入/描述全链自动完成，零配置代码）。

- **同进程单例**：改磁盘代码须退出重开 `python chat.py` 才生效。`%reset -f` 或 `globals().clear()` 清变量，不预置专门函数。
- **Python 3.8**：不用 `dict | merge`、`list[int]` 内置泛型、`removeprefix` 等。
- **单一事实源**：预置函数由 `tools/` 自动发现，技能由 `skills/*/SKILL.md` 自动发现。加东西只需创建文件。
- **最小预置**：标准库一行可完成的，不封装。
- **踩坑即前置**：模型踩过的坑写进 `prompt.txt` 或工具 docstring。

## Result 三元组

预置函数返回 `Result`（str/list/dict 子类）：
- 直接当原生类型用
- `.error`：成功为 None，非 None 表示函数自身失败
- `.facts`：附加事实字典，同时展开为属性

判断成败查 `.error`，不要用 `if not r:`。

## 预置函数（`tools/` 一函数一文件）

`read` `glob` `grep` `write` `edit` `bash` —— 探索、读、改、跑。

## 技能系统

`skills/<name>/SKILL.md` 带 YAML frontmatter。`skills.py` 自动扫描，正文按需 `read`（不预加载）。
