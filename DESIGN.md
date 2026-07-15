---
name: kernel-design
description: 基于 Cursor 设计语言的 AI 编程助手聊天界面，亮色/暗色双主题。
---

颜色基于 [Cursor DESIGN.md](awesome-design-md/design-md/cursor/DESIGN.md)。暗色从亮色同源推导。

## 主题切换

CSS 自定义属性 + `[data-theme]` 选择器。组件只引用 `var(--color-canvas)`，不感知当前主题。切换由 `<html data-theme="light|dark">` 控制。

## 色彩

### 亮色（data-theme="light"）

| 变量 | 值 | 用途 |
|------|-----|------|
| `--color-primary` | `#f54e00` | 主按钮、发送按钮（Cursor Orange） |
| `--color-primary-active` | `#d04200` | 按下态 |
| `--color-canvas` | `#f7f7f4` | 页面底色（暖奶油） |
| `--color-canvas-soft` | `#fafaf7` | 代码块背景 |
| `--color-surface` | `#ffffff` | 消息气泡背景 |
| `--color-hairline` | `#e6e5e0` | 气泡边框、分割线 |
| `--color-hairline-strong` | `#cfcdc4` | 输入框边框 |
| `--color-ink` | `#26251e` | 标题、强调 |
| `--color-body` | `#5a5852` | 正文 |
| `--color-muted` | `#807d72` | 辅助文字 |
| `--color-muted-soft` | `#a09c92` | 禁用文字 |
| `--color-on-primary` | `#ffffff` | 按钮文字 |
| `--color-thinking` | `#dfa88f` | 思考气泡背景 |
| `--color-thinking-border` | `#c8957a` | 思考左边框 |
| `--color-system` | `#e6e5e0` | 系统消息背景 |
| `--color-success` | `#1f8a65` | 执行成功 |
| `--color-error` | `#cf2d56` | 执行失败 |

### 暗色（data-theme="dark"）

| 变量 | 值 | 用途 |
|------|-----|------|
| `--color-primary` | `#ff6b2b` | 暗色下稍亮 |
| `--color-primary-active` | `#e55a1a` | 按下态 |
| `--color-canvas` | `#1e1e1c` | 暖暗底色 |
| `--color-canvas-soft` | `#252523` | 代码块背景 |
| `--color-surface` | `#2a2a28` | 气泡背景 |
| `--color-hairline` | `#383835` | 边框 |
| `--color-hairline-strong` | `#4a4a46` | 输入框边框 |
| `--color-ink` | `#f0f0ed` | 标题 |
| `--color-body` | `#b5b3ad` | 正文 |
| `--color-muted` | `#8a8882` | 辅助文字 |
| `--color-muted-soft` | `#6a6862` | 禁用文字 |
| `--color-on-primary` | `#ffffff` | 按钮文字 |
| `--color-thinking` | `#3a3028` | 思考气泡 |
| `--color-thinking-border` | `#5a4a3a` | 思考左边框 |
| `--color-system` | `#333330` | 系统消息 |
| `--color-success` | `#2ea87a` | 成功 |
| `--color-error` | `#e04060` | 失败 |

## 字体

| 用途 | 字体 | 大小 | 字重 | 行高 |
|------|------|------|------|------|
| 页面 | Inter, system-ui, sans-serif | 16px | 400 | 1.5 |
| 消息正文 | 同上 | 16px | 400 | 1.6 |
| 代码 | JetBrains Mono, Fira Code, monospace | 13px | 400 | 1.5 |
| 行内代码 | 同上 | 13px | 400 | — |
| 辅助文字 | Inter, system-ui, sans-serif | 13px | 400 | 1.4 |
| 小标签 | Inter, system-ui, sans-serif | 11px | 600 | 1.4 |
| 按钮 | Inter, system-ui, sans-serif | 14px | 500 | 1.0 |

## 间距

基于 4px 单位：`4 8 12 16 20 24 32 48`

- 消息间距：24px
- 气泡内边距：16px
- 代码块内边距：16px
- 输入区内边距：12px 16px

## 圆角

- 气泡：12px
- 代码块：8px
- 输入框：8px
- 按钮：8px

## 深度

无阴影。层级靠颜色区分：
- 画布 → 气泡（1px hairline 边框 + 表面色差）
- 气泡 → 代码块（canvas-soft 嵌入色）

## 组件

### 消息气泡（4 角色）

| 角色 | 背景 | 文字 | 对齐 | 图标 |
|------|------|------|------|------|
| 用户 | `--color-surface` | `--color-ink` | 右 | 👤 |
| 助手 | `--color-surface` | `--color-body` | 左 | 🤖 |
| 思考 | `--color-thinking` | `--color-body` | 左 | 💭 |
| 系统 | `--color-system` | `--color-muted` | 居中 | 📢 |

骨架：圆角 12px，内边距 16px，1px hairline 边框，最大宽度 80%。

### 思考区

对应 `display.py` 的 spinner 行。流式写入时实时显示 token 数和耗时：

`💭 思考中 · 123 tokens · 5s`

切换到回复时：

`💬 回复中 · 456 tokens · 12s`

flush 后显示完整思考内容，默认折叠。左边框 3px `--color-thinking-border`，点击展开/折叠。

### 代码块

默认折叠，显示一行摘要（和 `display.py` 的 `_fold_exec_blocks` 一致）：

`代码块 · 12 行 · print("hello")`

点击展开显示完整代码。语言标签在右上角（`--color-muted` 11px）。

### Markdown 渲染

助手消息用 react-markdown 渲染（GFM）：

- **标题**：`--color-ink`，字重 600
- **表格**：1px hairline 边框，偶数行 `--color-canvas-soft`
- **行内代码**：`--color-canvas-soft` 背景，JetBrains Mono 13px，圆角 4px，内边距 2px 6px
- **链接**：`--color-primary`
- **引用块**：左边框 3px `--color-hairline-strong`，`--color-muted` 文字
- **列表**：左缩进 24px
- **分割线**：1px `--color-hairline`

### 输入区

固定底部：
- 输入框：`--color-surface` 背景，1px `--color-hairline-strong` 边框，圆角 8px
- 发送按钮：`--color-primary` 背景，"发送" 白色文字，圆角 8px
- 禁用态：按钮和输入框变 `--color-muted-soft`
- 提示文字："输入消息..."（`--color-muted-soft`）

### 状态栏

顶部固定，显示连接状态：
- 🟢 已连接（`--color-success`）
- 🟡 连接中...（`--color-muted`）
- 🔴 已断开（`--color-error`）

### 主题切换按钮

状态栏右侧，单按钮切换亮色/暗色。图标：☀️ / 🌙。

## 已知缺口

- 语法高亮：需要 `react-syntax-highlighter`（当前未安装）
- 代码块折叠状态：需要在前端消息结构中加 `collapsed` 字段