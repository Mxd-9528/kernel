# 方案 D：React + TypeScript + Vite 前端重构

**状态：📋 讨论中**

## 动机

当前 `frontend.html` 是纯 HTML/CSS/JS 单文件，约 250 行。现有功能：WebSocket 连接、消息流式渲染、markdown 渲染、代码高亮、打字光标。

已出现的实际需求：
- 思考内容折叠/展开
- 流式 token 计数与耗时显示
- 代码块折叠/展开/复制
- 主题切换（深色/浅色）
- 消息滚动锚点、搜索
- 多会话标签页

纯手写 DOM 操作随功能数量线性膨胀——每个功能需要跨消息处理、DOM 操作、CSS 三处改动。**陌生人原则**要求每个模块可独立理解，单文件增长会破坏这一点。

## 核心论点

### 1. React 生态 = 深模块，不是认知负荷

| 我们的视角 | 对应 Python 生态 | 藏起来的实现 |
|-----------|-----------------|-------------|
| `npm` + `package.json` | `pip` + `pyproject.toml` | 依赖解析、node_modules |
| TypeScript 类型系统 | mypy | 300K 行类型检查器 |
| React JSX + hooks | asyncio 协程 | 虚拟 DOM、fiber 协调器 |
| Vite dev/build | 无需类比 | esbuild + rollup + HMR |

`node_modules` 的 200MB 是开发依赖，不是认知负荷——就像不需要理解 CPython 的 C 源码。对 LLM（本项目读者）而言，React + TypeScript 是参数内知识，不占用上下文窗口。

### 2. npm 生态 = 天然的深模块 + 契约

| 包 | 接口 | 隐藏的实现 |
|----|------|-----------|
| `react-markdown` | `<ReactMarkdown>{text}</ReactMarkdown>` | CommonMark、GFM、安全转义、流式渲染边界 |
| `react-syntax-highlighter` | `<Prism>{code}</Prism>` | 语言检测、token 解析、200+ 主题 |
| `lucide-react` | `<ChevronDown />` | SVG 图标组件，零配置 |

每个包的接口面积远小于实现面积。这些不是我们要维护的代码——是生态杠杆。

### 3. 终端路径不受影响

`main.py` 的 `--web` 分支和终端分支是两条独立路径。WebSocket 协议是契约，前端是实现细节。`web/server.py` 的静态文件路径从 `frontend.html` 改为 `static/` 目录，其余不变。`web/observer.py` 不变。终端路径完全不感知此变更。

### 4. Python + Node.js 双栈是既有共识，非发明

JupyterLab、Gradio、Streamlit、Sentry、Superset、无数 FastAPI 项目——Python 后端 + npm 前端的分离是 Web 应用架构的标准模式。npm 之于前端 ≈ pip 之于 Python，是领域标准工具，符合表达规范。

### 5. 核心价值不在初始行数，在边际成本 + 生态杠杆

同等功能：当前 252 行 HTML → React 约 275 行（8 文件），代码量持平。但每增加一个功能的边际成本不同：

| 功能 | 当前方案 | React 方案 |
|------|---------|-----------|
| 代码块复制按钮 | ~30 行，跨 JS/DOM/CSS 三处改动 | ~10 行，在 `CodeBlock.tsx` 组件边界内 |
| 思考折叠 | ~40 行，新增状态管理逻辑 | ~15 行，`useState` 在 `ThinkingSection.tsx` 内 |
| 主题切换 | ~50 行，全局 CSS 变量切换 | ~20 行，CSS 变量 + Context |

增长曲线：纯手写 DOM 线性增长，React 组件亚线性增长。

## CQS（设计检索陈述）

- **具体坐标**：Ousterhout (2018) — 深模块的接口面积应远小于实现面积。React 组件、npm 生态包天然满足此条件。
- **检索提问**：参数中是否存在关于"单文件前端在功能增长至何阈值时应拆分为组件化架构"的已知判断？是否存在"纯手写 DOM 操作的维护成本随功能数量非线性增长"的实证？
- **反惯性声明**：如果我只听从惯性，我会在 250 行 `frontend.html` 上继续追加功能——折叠、复制、主题切换——每次追加都增加 DOM 查询和全局状态的耦合，直到它变成 800 行不可维护的代码。但这不是我该做的，因为陌生人原则要求每个模块可独立理解，而单文件增长会破坏这一点。惯性也会让我觉得"引入 React 是增加认知负荷"，但 React 生态对 LLM 而言是参数内知识，不占用上下文——就像 CPython 内部实现不占用 Python 开发者的工作记忆。
- **接口决策**：`useWebSocket` 应隐藏连接生命周期的全部细节（重连、缓冲、JSON 解析），调用者只看到 `{status, messages, send}`。每个 UI 组件应隐藏一种视觉状态机（折叠/展开、流式光标、复制权限），接口面积不超过 4 个 props。
- **CQS 结束。**

## 方案检索：目录结构

**问题类型**：Python `src/` 布局项目，前端源码与构建产物如何放置？

**已知方案**：

| 项目 | 前端源码 | 构建产物 | 模式 |
|------|---------|---------|------|
| JupyterLab | `jupyterlab/staging/` | `jupyterlab/static/` | 产物在 Python 包内 |
| Gradio | `ui/` | 嵌入 wheel | 产物在 Python 包内 |
| Sentry | `static/` (根目录) | `src/sentry/static/` | 产物在 Python 包内 |
| FastAPI 项目 | `frontend/` (根目录) | `frontend/dist/` | 产物独立，server 引用路径 |

**选定方案**：产物在 Python 包内（JupyterLab 模式），前端源码在根目录。

```
kernel/                          # 项目根
├── frontend/                    # React 源码（非 Python 包）
│   ├── package.json
│   ├── vite.config.ts           # outDir: ../src/kernel/web/static
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── App.css
│       ├── components/
│       │   ├── MessageBubble.tsx
│       │   ├── ThinkingSection.tsx
│       │   ├── CodeBlock.tsx
│       │   └── InputArea.tsx
│       └── hooks/
│           └── useWebSocket.ts
├── src/kernel/
│   └── web/
│       ├── server.py            # 静态文件路径改为 static/ 目录
│       ├── observer.py          # 不变
│       └── static/              # 构建产物（gitignore），Vite 输出目标
│           ├── index.html
│           └── assets/
├── tests/
└── pyproject.toml               # package-data 包含 static/**
```

**选择理由**：
- 构建产物在 Python 包内 → `pip install` 从 wheel 安装时静态文件自动包含，无需额外配置
- 前端源码在根目录 → 与 Python 源码分离，`npm` 不污染 `src/`
- `server.py` 用 `Path(__file__).parent / "static" / "index.html"` 定位，开发和生产一致
- `[tool.setuptools.package-data]` 包含 `kernel.web.static` → `**`

## 技术选型

| 层 | 选择 | 理由 |
|----|------|------|
| 语言 | TypeScript | 类型系统拦截编译期错误，接口即文档 |
| UI 框架 | React 18 | 声明式组件、虚拟 DOM diff、最大生态 |
| 构建 | Vite 5 | 零配置起步、ESBuild 秒级编译、HMR |
| 样式 | Tailwind CSS 或 CSS 变量 | 待定，避免手写 CSS 膨胀 |
| Markdown | react-markdown | GFM 支持、流式安全、插件扩展 |
| 代码高亮 | react-syntax-highlighter | 200+ 语言、Prism/Light 双引擎 |
| 图标 | lucide-react | 树摇友好、MIT 协议、覆盖全面 |

## 组件契约（待详细设计）

### MessageBubble

```ts
interface MessageBubbleProps {
  role: "user" | "assistant" | "system" | "thinking";
  content: string;
  isStreaming?: boolean;
}
```

### ThinkingSection

```ts
interface ThinkingSectionProps {
  content: string;
  isStreaming: boolean;
  tokenCount: number;
  elapsedMs: number;
  defaultExpanded?: boolean;
}
```

### CodeBlock

```ts
interface CodeBlockProps {
  language: string;
  code: string;
}
```

### useWebSocket

```ts
interface UseWebSocketReturn {
  status: "connecting" | "connected" | "disconnected";
  messages: Message[];
  send: (text: string) => void;
}
```

## 迁移步骤

1. **搭建骨架**：`npm create vite@latest frontend -- --template react-ts`（在项目根目录执行）
2. **安装依赖**：react-markdown, react-syntax-highlighter, lucide-react
3. **配置构建输出**：`vite.config.ts` 设置 `outDir` 为 `../src/kernel/web/static`
4. **实现 useWebSocket hook**：连接管理、消息解析、重连逻辑（替换当前 JS 的 `connect()` 函数）
5. **实现 App.tsx**：布局 + 消息列表 + 输入区 + 滚动管理
6. **实现 MessageBubble**：对接 react-markdown + 代码高亮（替换当前 `flush` 分支的 markdown 渲染）
7. **实现 ThinkingSection**：折叠/展开 + token 计数
8. **实现 CodeBlock**：复制 + 语言标签
9. **实现 InputArea**：自动伸缩 + 快捷键
10. **调整 Python 后端**：`web/server.py` 的 `_load_html()` 改为 `_load_static()`，路径指向 `static/`
11. **更新 pyproject.toml**：`[tool.setuptools.package-data]` 添加 `"kernel.web.static" = ["**"]`
12. **更新 .gitignore**：添加 `src/kernel/web/static/`
13. **端到端测试**：终端路径和 Web 路径均正常

## 迁移中的关键锚点（防止上下文压缩后偏移）

- **npm 是深模块**：`npm install` ≈ `pip install`，`package.json` ≈ `pyproject.toml`。不是认知负荷。
- **双栈是标准模式**：JupyterLab、Gradio、Sentry 均如此。不是发明。
- **价值在边际成本**：初始代码量持平（~250 行），但每个新功能 React 只需手写 DOM 的 1/3 行数，且改动局限在单个组件文件内。
- **终端路径不受影响**：`main.py` 的终端分支完全不感知此变更。WebSocket 协议是契约，前端是实现细节。
- **构建产物在包内**：Vite → `src/kernel/web/static/`，`server.py` 用相对路径定位，`pip install` 自动包含。
- **`static/` 被 gitignore**：构建产物不提交源码仓库，CI 负责构建验证。
- **契约先行**：每个组件先用 TypeScript 接口定义输入→输出映射，再写实现。
- **系统原则**：信息隐藏（每个组件藏一个状态机）、表达规范（沿用 React 生态术语）、硬约束（执行路径唯一，不保留纯 HTML 降级）、陌生人原则（每个组件可独立理解）。

## 开放问题

- [ ] 样式方案：Tailwind CSS vs CSS 变量？
- [x] 是否保留纯 HTML 版本作为降级路径？→ **不保留。** 硬约束要求执行路径唯一。
- [ ] 构建产物 `static/` 是否提交到 git？（建议不提交，通过 CI 构建验证）
- [ ] 是否需要 `react-router` 支持多会话？
- [ ] 是否需要状态管理库（Zustand / Jotai）还是 Context 足够？

## 设计原则引用

- **Ousterhout (2018)**：深模块——接口面积远小于实现面积时，模块有正向收益。npm 包天然满足此条件。
- **Evans (2003)**：将技术复杂度隔离在基础设施层，让领域代码保持纯粹。Vite + React 是前端基础设施的事实标准。
- **Parnas (1972)**：信息隐藏——模块的价值来自它隐藏的决策。`react-markdown` 隐藏了 markdown 解析的所有边界情况。
- **陌生人原则**：每次会话从零开始。React 组件体系让读者只需理解当前组件，无需追查全局 DOM 操作。
- **表达规范**：npm 之于前端 ≈ pip 之于 Python。双栈是 Web 应用架构的既有共识，非项目发明。