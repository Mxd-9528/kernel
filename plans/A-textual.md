# 方案 A：TUI 框架（Textual）

**状态：❌ 已排除**

## 思路

用 Textual 替代 Rich。Textual 是 Rich 的兄弟项目，专为交互式 TUI 设计——它接管整个终端，管理输入/输出区域的布局，处理所有 ANSI 细节。observer 协议不变，`_Spinner` 重写为 Textual App。

## 架构映射

```
observer.on_delta → Textual widget.update(token) → 框架自动重绘
observer.on_flush  → 停止 spinner，渲染完整回复
用户输入           → Textual Input widget → chat() 收到消息
```

## 排除原因

1. **终端本身的限制无法突破**。字体大小、行距、排版——这些都是终端模拟器的能力边界，任何 TUI 框架都无法改变它们。Textual 的默认面板在视觉上甚至不如当前的 Rich 输出。

2. **已经尝试过**。结论是：在终端内无论用什么框架，上限都是"终端能显示的最好的东西"。而"终端能显示的最好的东西"远不如浏览器能显示的最基本的东西。

3. **根本问题不在框架**。问题不是"Python 有没有好的 TUI 库"，而是"终端是不是交互式富文本显示的正确平台"。答案是否定的。它是一台 1970 年代的打字机模拟器，不是 2025 年的渲染引擎。
