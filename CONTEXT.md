# CONTEXT

本项目的设计思想沿用五本经典软件工程文献。本文档说明这些原则在"调用者为无状态大语言模型 (LLM)"这一场景下如何具体化落地。

## 参考文献

- Parnas, D. L. (1972). *On the Criteria To Be Used in Decomposing Systems into Modules.* —— 信息隐藏 (Information Hiding)。
- Gamma, E., Helm, R., Johnson, R., Vlissides, J. (1994). *Design Patterns.* —— *Program to an interface, not an implementation.*
- Martin, R. C. (1996 / 2000). *SOLID Principles.* —— 依赖倒置原则 (Dependency Inversion Principle, DIP)。
- Beck, K. (1999). *Extreme Programming Explained.* —— YAGNI (You Aren't Gonna Need It)。
- Ousterhout, J. (2018). *A Philosophy of Software Design.* —— 深模块 (Deep Module)、认知负荷 (Cognitive Load) 最小化。

## 元决策：调用者是无状态 LLM

传统软件工程假设读者是人类工程师，具有跨会话记忆。本项目的读者是 LLM——每次会话从零开始，不保留上一次的上下文。

由此产生一条新约束：**每次会话所需读取的代码量应当最小化**。项目采用的方法不是扩大 LLM 的记忆容量（更长上下文、检索增强、多层摘要），而是通过既有经典原则（信息隐藏、深模块、依赖倒置）把复杂度封装在少数稳定接口之后，使调用者读接口即可正确使用，无需下潜实现。

以下章节说明五条经典原则的具体落地。

## 1. 信息隐藏 (Information Hiding, Parnas 1972)

**原则**：模块内部的实现决策对外不可见。调用者只依赖模块的公开接口。

**落地**：项目分两层文件：

- **接口层**：`call.py` / `background.py` / `compact.py` / `run.py`。文件名无下划线前缀。内容为 10–25 行的公开 API 声明（模块 docstring 描述签名、返回值、失败模式、跨层协议），末尾通过 `from _xxx import ...` 从实现层重导出符号。
- **实现层**：`_call.py` / `_background.py` / `_compact.py` / `_run.py`。文件名带下划线前缀 (PEP 8 私有命名约定，同 CPython 的 `_ssl` / `_socket` / `_json`)。承载全部实现细节：线程、锁、协议解析、IPython 内部对象等。

调用方读接口层即可完成开发。实现层文件仅在维护该模块本身时阅读。

## 2. 面向接口编程 (Program to an interface, not an implementation; Gamma et al. 1994)

**原则**：调用方依赖抽象，不依赖具体实现。

**落地**：所有上游代码只写 `from call import call`，禁止 `from _call import call`。接口层文件是唯一被上游 import 的对象；实现层的存在对上游透明。若未来需替换实现（例如 `_call.py` 从 REST 换成 gRPC），接口层文件与所有上游 import 语句均不变。

## 3. 依赖倒置原则 (Dependency Inversion Principle, Martin 1996)

**原则**：高层模块与低层模块都依赖抽象，不互相直接依赖；抽象由调用者与架构师定义，实现服从抽象。

**落地**：
- 接口的签名、返回、异常契约由调用方需求驱动，非由实现方便性驱动。
- 接口与实现出现冲突时，先修改实现使其符合接口，除非架构师明确决定修订接口。
- `tests.py` 通过对象同一性断言 (`call.call is _call.call`) 检测接口与实现是否漂移。

## 4. 深模块 (Deep Module, Ousterhout 2018)

**原则**：模块价值等于"接口简单度"与"封装的复杂度"之乘积。接口越窄、实现越厚，抽象价值越高。浅模块 (接口面积接近实现面积) 增加认知负荷而不提供抽象收益。

**落地**：`call` / `background` / `compact` / `run` 均属深模块：

| 接口层行数 | 实现层行数 | 封装内容 |
|---|---|---|
| `call.py` 17 | `_call.py` ~90 | HTTP 请求组装、鉴权、.env 加载、reasoning_content 剥离 |
| `background.py` 22 | `_background.py` ~120 | 线程池、超时监控、结果持久化、任务状态机 |
| `compact.py` 14 | `_compact.py` ~110 | 对话历史拆分、轮次计数、结构化压缩提示词、事实/提炼两层方法论 |
| `run.py` 19 | `_run.py` ~70 | IPython InteractiveShell 生命周期、stdout/stderr 捕获、ANSI 清洗、Result 分类 |

准入门槛（缺一不满足则不封装为深模块）：
1. 功能已收敛，对外能力清单基本稳定。
2. 接口 10–25 行足以覆盖全部对外行为。
3. 调用方无需继承、无需访问私有属性、无需感知内部数据结构。

## 5. 静态可验的依赖判据

**原则**：面向接口编程的合规性应当可以静态检查，不依赖运行时行为观察。

**落地**：任何上游 `.py` 文件的源码中，不应出现私有实现模块名 (`_call` / `_background` / `_compact` / `_run`) 作为 import 目标。运行时的函数调用链 (`call.call` 转发到 `_call.call`) 与源码可见的静态依赖是两个概念——静态依赖限定为 `import` 语句，只要 import 图不出现 `_xxx` 即为合规。

判据实现：`tests.py` 用正则扫描所有 `.py` 文件的 `from _xxx import` 与 `import _xxx` 语句；命中即为封装泄漏 (encapsulation leak)。接口文件本身与测试文件豁免（前者是唯一合法转手点，后者拥有跨层测试特权）。

## 6. 认知负荷最小化的其他手段

**同进程单例内核**：所有可执行逻辑均为 IPython InteractiveShell 命名空间中的普通 Python 函数，不存在编排层、工具层的架构分层。模型生成的代码块与预置函数通过同一条 `run()` 路径执行，返回统一的 `Result` / `ListResult` / `DictResult`。代价是修改磁盘代码需重启进程（强隔离通过子进程 `bash('python -c ...')` 实现）；收益是概念数量最少，调用方无需理解多层调度机制。

**约定优于配置 (Convention over Configuration)**：新增能力通过创建文件自动接入，无需注册。四层机制：
- `load.py` 将机件注入内核命名空间。
- `manifest.py` 扫描 `tools/` 目录发现预置函数。
- `skills.py` 扫描 `skills/*/SKILL.md` 发现技能。
- 接口层文件（无下划线的 `call.py` 等）通过命名约定自动构成"已封装模块"清单。

**统一反馈接口**：所有预置函数返回 `Result`（`str` / `list` / `dict` 的子类），可直接当作原生类型使用。成败通过 `.error` 属性判断（`None` 为成功），不使用 `if not r:` 这类基于真值的判断——因为 `Result("")` 为假但代表成功（空 stdout）。

## 硬约束

1. **执行路径唯一**：模型生成代码块与预置函数走同一条 `run()`，返回同一套 Result 三元组。
2. **反馈接口统一**：成败查 `.error is None`，不用 `if not r:`。
3. **模块可反射**：所有模块与函数可通过 `inspect` 获取源码、签名、路径。
4. **不重造 IPython 已有能力**：持久化命名空间、REPL 循环、异常捕获、magic 命令，已由 IPython 提供的不二次实现。
5. **最小预置**：Python 标准库一行代码可完成的操作，不封装为预置函数。
6. **Python 3.8 兼容**：不使用 3.9+ 语法 (`dict |`、`list[int]`、`str.removeprefix` 等)；`ruff` 配置 `target-version = "py38"` 自动检查。

## YAGNI (Beck 1999)

每次增删代码通过三个问题过滤：

1. 此改动的功能当前是否有明确调用需求？无则不写。
2. 若需要，标准库、已引入依赖、命名空间中已存在对象是否可以直接完成？可以则不新增代码。
3. 若必须新增，是否可以封装为深模块（接口 10–25 行覆盖对外行为）？可以则封装，不可以则平铺。

## 不适合封装的模块

以下模块不做接口/实现分离，因为不满足深模块准入门槛：

- `result.py`：调用者继承 `Result` / `ListResult` / `DictResult` 类本体，接口层无法只导出符号。
- `history.py` / `agent.py` / `extract.py`：调用者少（一到两处）或本身为编排层，封装带来的接口维护成本超过节省的认知负荷。
