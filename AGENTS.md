# AGENTS.md

kernel 项目的 AI 阅读入口。本文件自动加载，讲**怎么做**；宪法讲**为什么**。

> **[CONSTITUTION.md](CONSTITUTION.md)** 是本项目最高准则（元规则、硬约束、增负信号）。做架构决策、设计新模块、判断是否新增抽象时，先 `read("CONSTITUTION.md")`。日常改动无需读。

## 导航

按你要动的位置读对应文件——不必读全部。

| 位置 | 阅读入口 | 内容 |
|---|---|---|
| Python 内核 | [src/kernel/AGENTS.md](src/kernel/AGENTS.md) | 主循环、注入、系统提示词组装 |
| 预置函数 | [src/kernel/tools/AGENTS.md](src/kernel/tools/AGENTS.md) | 添加新工具的契约 |
| Web/WebSocket | [src/kernel/web/AGENTS.md](src/kernel/web/AGENTS.md) | JSON-RPC 消息、Observer 协议 |
| 前端 | [frontend/AGENTS.md](frontend/AGENTS.md) | Vite、测试目录、组件约定 |

宪法与项目概述：
- [CONSTITUTION.md](CONSTITUTION.md) — 设计原则（按需手动读）
- [README.md](README.md) — 用户入门

## Essential Commands

```bash
make install    # 装所有依赖（Python + 前端）
make test       # 跑全部测试
make build      # 前端构建到 src/kernel/web/static/
make lint       # Python + 前端代码检查

ma              # 启动终端对话
ma --web        # 启动 WebSocket 服务端（端口 8765）
```

## 硬规则（可机械检查）

- **文件 <300 行 / 函数 <40 行**——超出即为混合了多个关注点，拆分。
- **顶层 import**——除非按需加载的可选依赖，不写函数内 import。
- **早返回**——守卫子句在前，避免深嵌套。
- **pathlib 优先**——新代码不用 `os.path`。
- **stdlib 一行能做的不封装**——宪法硬约束的机械化版本。
- **不发明项目专属术语**——沿用 Python/软件工程既有词汇。

## 提交约定

沿用 Conventional Commits：`feat / fix / refactor / docs / test / ci`。
scope 用目录名：`kernel / tools / web / frontend`。
