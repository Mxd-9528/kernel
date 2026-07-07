# 哲学与裂缝

## 核心命题

传统软件工程假设读者是人类工程师，具有跨会话记忆。本项目读者是 LLM——每次会话从零开始。由此产生一条硬约束：**每次会话所需读取的代码量应当最小化**。

Parnas 的信息隐藏、Ousterhout 的深模块、Fowler 的重构自明、Beck 的 YAGNI、Maeda 的删到无憾——这些经典原则在此场景下从"最佳实践"升级为"生存约束"。过度阅读不只是低效，是不可能。

## 为"永远陌生的读者"写作

LLM 没有入职过程、没有走廊对话、没有积累的语境。它每次打开文件都是第一次也是唯一一次。这意味着：

- **代码必须是自证的**——不能依赖读者"已经知道"为什么这样设计。注释不是代码的补充，是代码失败的证据（Fowler）。
- **隐藏即仁慈**——Parnas 的信息隐藏不只是为变更管理，而是免除读者"知道某物存在"的义务。你不必知道你不知道。
- **接口即合同**——读者只需要读接口文件，不需要读实现。`call.py`（3 个符号）对 `_call.py`（62 行）的 re-export 就是典范。
- **导航必须自明**——文件命名、目录结构、导入路径本身即导航，不需要额外地图。约定优于配置。
- **每多一行代码，就是对陌生读者多一次认知征税**——YAGNI 从工程策略变成认识论义务。

## 代码评估：整体对齐

项目 11 个核心模块中，大多数是对自己哲学的忠实实现。`call.py`、`compact.py`、`edit.py` 是深模块的典范——接口极窄，实现极厚，调用者不需要读实现。`agent.py` 一个 `agent()` 函数隐藏 184 行循环逻辑和超时保护。`survey.py` 的缓存自动失效对调用者完全透明。`edit.py` 的花引号归一化是"隐藏决策以服务陌生人"的教科书案例。

## 四条裂缝

### 1. `agent.py:52-53` —— 异常上的隐式约定

`_run_cell` 在异常对象上挂载 `_kernel_stdout` / `_kernel_stderr` 自定义属性，`feedback` 通过 `getattr` 反向读取。两个函数之间的约定是隐式的，陌生读者需要跨函数追踪才能理解。

**修法：** 用 `dataclass` 或 `namedtuple` 包装 `(stdout, stderr, exception)` 三元组，让 `_run_cell` 返回它，`feedback` 解构它。消灭猴子补丁，把约定变成显式类型。

### 2. `tools/read.py:29` —— `offset or 1` 的静默行为

`start = (offset or 1) - 1` 让 `offset=0` 和 `offset=None` 行为相同（都从第 1 行开始），但 docstring 声明"从 1 开始计数"。`offset=0` 应报错而非静默修正。

**修法：** `start = (offset if offset is not None else 1) - 1`，或对 `offset=0` 显式抛 `ValueError`。

### 3. `_call.py:56` —— 硬编码 HTTP 超时会导致长输出对话崩溃

非流式请求下，`urllib.request.urlopen(req, timeout=90)` 的 90 秒硬超时覆盖整个响应接收过程。模型输出一个长回复（如生成几百行代码文件）时，如果模型端生成+传输超过 90 秒，连接直接断开，整个对话崩溃。这是可恢复的损失——模型已经生成的内容全丢。

**修法：** 删掉 `timeout=90` 参数。`urllib.request.urlopen` 默认无超时，等待模型完整输出即可。socket 层的 TCP keepalive 足够处理真正的网络僵死。

### 4. `chat.py:66` —— history 落盘时机滞后，中间状态全在内存

`save(messages)` 在 `agent()` 整个执行循环**返回之后**才调用。一次 agent 调用可能包含 1-20 轮 `<!EXEC>` 循环，每轮都更新了 `messages`。如果中间发生内核崩溃、进程被 kill、Ctrl+C 强杀，所有这些中间状态全丢——用户丢失一个完整对话回合。

**修法：** 把 `save()` 下沉到 `agent()` 内部，每次 `messages` 被修改后立即落盘。具体位置：`agent()` 循环内，`messages.append(assistant)` 之后和 `messages.append(feedback)` 之后各调一次 `save()`。
