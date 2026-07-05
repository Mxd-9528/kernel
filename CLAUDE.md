# CLAUDE.md

设计思想见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)。

## 项目概述

基于持久 IPython 内核的自驱动 agent。模型输出 `<!EXEC>` 包裹的 Python 代码块，经 `run()` 在内核中执行并将结果反馈回模型，循环至任务完成。预置函数是预加载进内核命名空间的普通 Python 函数，不是工具调用协议 (function calling) 意义上的工具。

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
| `agent.py` | 自驱动循环：LLM 回复 → 提取代码块 → 执行 → 反馈 → 重复 |
| `call.py` / `_call.py` | LLM 调用接口 / 实现 |
| `background.py` / `_background.py` | 后台任务接口 (超时转后台、状态查询、取消) / 实现 |
| `compact.py` / `_compact.py` | 上下文压缩接口 (触发判定、结构化摘要) / 实现 |
| `run.py` / `_run.py` | 代码执行接口 (持久 IPython 单例、Result 三元组) / 实现 |
| `extract.py` | 从模型回复中提取 `<!EXEC>` 代码块 |
| `result.py` | `Result` / `ListResult` / `DictResult`：Body + `.error` + `.facts` |
| `inject.py` | `shell.push` 将对象推入 IPython `user_ns`，幂等 |
| `load.py` | 机件注入锚点（约定优于配置的接入点之一） |
| `manifest.py` | `tools/` 目录自动发现 |
| `skills.py` | `skills/*/SKILL.md` 自动发现 |
| `history.py` | 对话历史持久化 |
| `models.json` | LLM 端点配置；默认模型为首个键 |

## 面向接口编程 (Program to an interface, not an implementation; Gamma et al. 1994)

**接口层与实现层分离**：接口占用无下划线的公开名 (`call.py`)，实现下沉带下划线前缀 (`_call.py`)。此为 PEP 8 私有命名约定，与 CPython 标准库 `_ssl` / `_socket` / `_json` 同构。

**上游依赖规则**：

- 所有 `.py` 文件（包括模型生成的 `<!EXEC>` 代码块）import 底层能力时只写 `from call import ...` / `from background import ...` / `from compact import ...` / `from run import ...`。
- 禁止 `from _call import ...` 及同类形式；下划线前缀的模块名不应出现在上游源码中。
- 接口与实现出现冲突时，修改实现使其符合接口，除非架构师明确决定修订接口。
- 新增接口 (封装为深模块) 的准入门槛：功能已收敛、接口 10–25 行覆盖对外全部行为、上游无需访问实现内部。

**静态验证**：`tests.py` 通过正则扫描所有 `.py` 文件，检测 `from _xxx import` 与 `import _xxx` 语句。命中即为封装泄漏 (encapsulation leak)。接口文件本身与 `tests.py` 豁免（前者为唯一合法转手点，后者拥有跨层测试特权）。

## Result 三元组

预置函数返回 `Result` 或其子类 (`ListResult` / `DictResult`)。三个组成部分：

1. **Body**：`Result` 是 `str` 子类，`ListResult` 是 `list` 子类，`DictResult` 是 `dict` 子类；可直接当原生类型使用。
2. **`.error`**：成败判据。`None` 表示成功；非 `None` 时携带原生异常对象，可 `raise` / `isinstance` 判断。**不使用 `if not r:`**，因为 `Result("")` 为假但代表成功（空 stdout）。
3. **`.facts`**：附加事实字典，键同时展开为对象属性 (`r.facts["task_id"]` 等价于 `r.task_id`)。

## 预置函数

`tools/` 目录，一函数一文件，`manifest.py` 自动发现：`read` / `glob` / `grep` / `write` / `edit` / `bash` / `task_status` / `task_cancel`。

## 技能

`skills/<name>/SKILL.md` 文件，含 YAML frontmatter；`skills.py` 扫描注册元数据；正文按需通过 `read()` 加载。

## 硬约束

- **同进程单例**：修改磁盘代码后需重启 `python chat.py`。强隔离通过子进程 (`bash('python -c ...')`) 实现，不通过重置内核。
- **Python 3.8 兼容**：不使用 `dict |`、`list[int]`、`str.removeprefix` 等 3.9+ 语法。
- **约定优于配置**：`tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动接入，新增能力仅需创建文件。
- **最小预置**：Python 标准库一行代码可完成的操作不封装为预置函数。
