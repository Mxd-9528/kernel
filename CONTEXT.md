# CONTEXT.md

**项目概述**

kernel 是一个基于 IPython 持久内核的 LLM agent 循环。用户输入自然语言，LLM 回复中包含 `<EXEC>...</EXEC>` 代码块，代码在持久 IPython 内核中执行，执行结果反馈给 LLM，循环直到 LLM 回复不含代码块为止。

每次会话是一个持久 Python 进程。模型在用户命名空间里定义变量、导入模块、写函数——这些对象跨轮保留，直到进程退出。history.json 存对话历史，启动自动接续。

**核心循环**

```
用户输入 → agent() → LLM 流式回复 → 提取 <EXEC> 代码块 → 执行 → 反馈 → LLM → ... → 纯文本回复（终止）
```

agent.py 中的 `agent()` 是循环主体。每轮最多 20 次迭代。Ctrl+C 通过 stop_event 优雅中断当前轮。

**模块地图**

| 模块 | 职责 | 被谁依赖 |
|------|------|----------|
| `main.py` | 入口：组合观察者，启动 chat | — |
| `chat.py` | 对话主循环：读输入、处理斜杠命令、调用 agent | main |
| `agent.py` | 决策-执行-观察循环，observer 从参数注入 | chat |
| `observer.py` | Observer 协议：6 个通知方法 + BaseObserver + CompositeObserver | agent, chat, compact, display, history |
| `runtime.py` | 提取 `<EXEC>` 块、在 IPython 内核执行、格式化反馈 | agent |
| `inject.py` | 首次执行时把机件和预置函数推入 IPython user_ns | runtime |
| `llm.py` | 读 models.json + .env，流式调用 LLM API | agent, compact |
| `system.py` | 扫描 tools/ 和 skills/，组装系统提示词 | chat, history |
| `history.py` | 对话历史持久化到 history.json（_HistoryObserver 实现 save） | chat |
| `compact.py` | 上下文压缩：保留 system + 最近 6 轮，摘要中间（_CompactObserver 实现 before_send） | chat |
| `display.py` | 流式输出渲染（_Spinner 继承 BaseObserver） | chat |
| `commands.py` | 斜杠命令：/new /model /help | chat |
| `tools/` | 预置函数包，每模块一个同名函数，由 system.py 扫描注册 | inject, system |
| `skills/` | 技能包，每个子目录一个 SKILL.md，按需 read() 加载 | — |
| `tests.py` | 核心 harness 测试 | — |
| `tests_tools.py` | 预置函数测试 | — |

**Observer 协议**

agent 循环通过 `observer` 参数在 6 个关键节点通知外部：

- `on_thinking(token)`：收到 reasoning token → display 更新思考中 spinner
- `on_delta(token)`：收到正文 token → display 更新回复中 spinner
- `on_flush()`：流结束 → display 一次性渲染累积正文
- `before_send(messages, model)`：发 LLM 请求前 → compact 压缩上下文
- `save(messages)`：消息列表变更 → history 存盘
- `display_msg(content)`：显示命令结果等非流式消息 → display 输出

main.py 通过 `CompositeObserver([spinner, compact_observer, history_observer])` 显式组合观察者。agent() 默认 `BaseObserver()`（静默），调用者按需注入。

**注入机制**

inject.py 只在首次执行时把机件（agent、chat、compact 等）和 tools/ 下的预置函数推入 IPython 的 user_ns。哨兵 `_kernel_injected` 防止重复注入——这保证模型在会话中重绑定预置函数后不会被覆盖，是"持久内核"价值的前提。

**系统提示词组装**

system.py 的 `build_system()` 按固定顺序拼接：prompt.md → 预置函数清单（扫描 tools/ 的签名+docstring） → 技能清单（扫描 skills/ 的 YAML frontmatter） → 可选的 system_append.md。

**预置函数**

tools/ 下每个模块暴露一个与模块同名的函数。system.py 通过 `pkgutil.iter_modules` + `getattr(mod, info.name)` 自动发现。新增预置函数只需在 tools/ 下创建 `工具名.py` 并定义同名函数，无需修改注册表。

**配置**

- `models.json`：LLM 模型列表，key 为模型别名，value 含 url/model/key_env
- `.env`：API key 等环境变量（setdefault 不覆盖已有）
- `history.json`：对话历史持久化文件
- `prompt.md`：系统提示词主体
- `compact_prompt.md`：上下文压缩用提示词
- `system_append.md`：可选，拼在系统提示词末尾

**测试**

`python tests.py` 跑核心 harness 测试（extract/agent/manifest/inject/feedback）。
`python tests_tools.py` 跑工具预置函数测试（read/glob/grep/write/edit/bash/plan/survey/bg_start）。
