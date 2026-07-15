# 方案 D：React + TypeScript + Vite 前端重构

**状态：📋 讨论中**

## 动机

当前 `frontend.html` 是纯 HTML/CSS/JS 单文件，约 250 行。现有功能：WebSocket 连接、消息流式渲染、markdown 渲染、代码高亮、打字光标。

可预见的功能增长：
- 思考内容折叠/展开
- 流式 token 计数与耗时显示
- 代码块折叠/展开/复制
- 主题切换（深色/浅色）
- 消息滚动锚点、搜索
- 多会话标签页

纯手写 DOM 操作会随功能线性膨胀，最终变成不可维护的屎山代码。**陌生人原则**要求基础架构能承载全生命周期增长。

## 核心论点

### 1. 构建工具链 = 深模块，不是认知负荷

```
开发者看到的：                   藏起来的（不需要理解）：
  src/App.tsx         ← 声明式    node_modules/    ← 实现细节
  npm run dev         ← 启动      vite.config.ts   ← 生成后几乎不动
  npm run build       ← 产出      esbuild/rollup/… ← Vite 内部
```

`node_modules` 的 200MB 磁盘占用是开发依赖，不是认知负荷——开发者不需要理解它，就像不需要理解 CPython 的 C 源码。

### 2. npm 生态 = 天然的深模块 + 契约

| 包 | 接口 | 隐藏的实现 |
|----|------|-----------|
| `react-markdown` | `<ReactMarkdown>{text}</ReactMarkdown>` | CommonMark、GFM、安全转义、流式渲染边界 |
| `react-syntax-highlighter` | `<Prism>{code}</Prism>` | 语言检测、token 解析、200+ 主题 |
| `lucide-react` | `<ChevronDown />` | SVG 图标组件，零配置 |

每个包的接口面积远小于实现面积。我们不需要发明这些。

### 3. 终端路径不受影响

`main.py` 的 `--web` 分支只做两件事：启动 WebSocket 服务端，提供 HTTP 静态文件。唯一变化是提供 `dist/` 目录而非单个 `frontend.html`。Python 后端接口不变，契约不变，测试不变。

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

## 目录结构（提案）

```
kernel/
├── main.py                  # 不变
├── websocket_server.py       # 不变
├── websocket_observer.py     # 不变
├── pyproject.toml            # 不变
├── frontend/                 # 新增：前端项目
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html            # Vite 入口模板
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── MessageBubble.tsx    # 消息气泡（markdown 渲染、代码高亮）
│       │   ├── ThinkingSection.tsx  # 思考折叠（展开/折叠状态）
│       │   ├── CodeBlock.tsx        # 代码块（折叠、复制、语言标签）
│       │   └── InputArea.tsx        # 输入区（自动伸缩、快捷键）
│       ├── hooks/
│       │   └── useWebSocket.ts      # 连接管理（重连、消息解析）
│       └── styles/
│           └── index.css
└── dist/                     # 构建产物（gitignore）
```

## 组件契约（待详细设计）

### MessageBubble

```ts
interface MessageBubbleProps {
  role: "user" | "assistant" | "system" | "thinking";
  content: string;
  isStreaming?: boolean;
  tokenCount?: number;
  elapsedMs?: number;
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
  defaultExpanded?: boolean;
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

## 迁移步骤（提案）

1. **契约先行**：定义组件树和接口，写出测试用例
2. **搭建骨架**：`npm create vite@latest frontend -- --template react-ts`
3. **安装依赖**：react-markdown, react-syntax-highlighter, lucide-react
4. **实现 useWebSocket hook**：连接管理、消息解析、重连逻辑
5. **实现 MessageBubble**：对接 react-markdown + 代码高亮
6. **实现 ThinkingSection**：折叠/展开 + token 计数
7. **实现 CodeBlock**：折叠/复制 + 语言标签
8. **实现 InputArea**：自动伸缩 + 快捷键
9. **调整 Python 后端**：静态文件路径改为 `dist/`
10. **端到端测试**：确保终端路径和 Web 路径均正常

## 开放问题

- [ ] 样式方案：Tailwind CSS vs CSS 变量 vs CSS Modules？
- [ ] 是否保留纯 HTML 版本作为降级路径？
- [ ] 构建产物 `dist/` 是否提交到 git？（建议不提交，通过 CI 构建）
- [ ] 是否需要 `react-router` 支持多会话？
- [ ] 是否需要状态管理库（Zustand / Jotai）还是 Context 足够？

## 设计原则引用

- **Ousterhout (2018)**：深模块——接口面积远小于实现面积时，模块有正向收益。npm 包天然满足此条件。
- **Evans (2003)**：将技术复杂度隔离在基础设施层，让领域代码保持纯粹。Vite + React 是前端基础设施的事实标准。
- **Parnas (1972)**：信息隐藏——模块的价值来自它隐藏的决策。`react-markdown` 隐藏了 markdown 解析的所有边界情况。
- **陌生人原则**：每次会话从零开始。React 组件体系让读者只需理解当前组件，无需追查全局 DOM 操作。
