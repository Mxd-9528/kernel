# CLAUDE.md

> 设计哲学见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## What this project is

持久 IPython 内核上的极简自驱动 agent。模型写 `<!EXEC>` Python 代码块感知并改变环境，循环到任务完成。

**不是工具调用范式**——预置函数只是预加载进内核命名空间的普通 Python 函数。

**统一命名空间公理**：项目模块、预置函数、模型生成代码无本质区别，均为命名空间一等公民。

**架构范式**：项目架构服务于 AI，不是反过来。用**沉淀线**（`*_contract.py` 合同文件）把已收敛的底层模块沉到"每次对话不必读"的水线以下。详见 CONTEXT.md。

## 命令速查

```bash
pip install -e .          # 装依赖
python chat.py            # 启动对话
python tests.py           # 跑全部测试
uvx ruff check .          # py38 静态检查
```

对话内：`exit` 退出，`/new` 清历史，`/model <名>` 切换模型。

## 文件职责

| 文件 | 职责 |
|---|---|
| `chat.py` | 交互入口：输入、斜杠命令、调 agent、历史 |
| `agent.py` | 自驱动循环：LLM → 执行代码块 → 反馈 → 重复 |
| `call.py` / `call_contract.py` | LLM REST 调用 / **合同（沉淀线）** |
| `background.py` / `background_contract.py` | 后台任务（超时转后台、状态、取消）/ **合同** |
| `extract.py` | 从回复抠 `<!EXEC>` 代码块 |
| `run.py` | 持久 IPython 单例执行，铸 Result 三元组 |
| `result.py` | `Result` / `ListResult` / `DictResult`：Body + `.error` + `.facts` |
| `inject.py` | `shell.push` 推入内核 user_ns，幂等 |
| `load.py` | 机件注入锚点（同构发现之一） |
| `manifest.py` | `tools/` 自动发现（同构发现之二） |
| `skills.py` | `skills/*/SKILL.md` 自动发现（同构发现之三） |
| `history.py` / `compact.py` | 对话持久化 / 上下文压缩 |
| `models.json` | LLM 端点配置，默认 = 首个键 |

## 沉淀线（合同文件）

**规则**：上游只 `from <模块>_contract import ...`，不 import 实现模块。改实现只要合同不变，上游零波及。

**已沉**：`call_contract.py`（22 行）、`background_contract.py`（22 行）。
**新沉门槛**：功能收敛 + 合同 10-25 行能覆盖对外全部行为 + 上游不摸内部。缺一不沉。

`tests.py` 有签名一致断言防漂移；改实现签名时同步改合同。

## 关键约束（速记）

- **同进程单例**：改磁盘代码须退出重开 `python chat.py`。
- **Python 3.8**：不用 `dict |`、`list[int]`、`removeprefix`。
- **单一事实源**：工具 `tools/`、技能 `skills/*/SKILL.md` 自动发现，加东西只需建文件。
- **最小预置**：标准库一行能做的不封装。
- **踩坑即前置**：坑写进 `prompt.txt` 或工具 docstring。

## Result 三元组

预置函数返回 `Result`（str/list/dict 子类）：直接当原生类型用；`.error` 判断成败（不用 `if not r:`）；`.facts` 附加事实同时展开为属性。

## 预置函数

`tools/` 一函数一文件：`read` `glob` `grep` `write` `edit` `bash` `task_status` `task_cancel`。

## 技能

`skills/<name>/SKILL.md` 带 YAML frontmatter，`skills.py` 扫描，正文按需 `read`。
