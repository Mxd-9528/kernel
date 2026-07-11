# Textual 迁移计划

## 目标

把 display 渲染后端从 Rich Live 替换为 Textual，解决 Live 超屏重复刷屏问题，并为后续折叠代码块铺路。

## 不变量

- `agent.py` 零改动。事件钩子（`on`/`emit`）不变。
- `display.py` 的 `on_delta`/`on_display`/`on_flush` 接口不变。
- 所有现有测试保持通过。

## 架构决策

| 决策 | 选择 | 理由 |
|------|------|------|
| App 生命周期 | 常驻全屏 | 折叠需要持续 UI，不能每轮进出 |
| 事件循环协调 | worker 线程 | agent.py 零改动 |
| 斜杠命令 | 输入框内识别 `/` | 保持现有交互习惯 |
| Ctrl+C | Textual keybinding | 全屏下 signal 不可靠 |
| 折叠功能 | 本次不做 | 迁移 + 输入重写已够大，增量加 |

## 步骤

### 第 1 步：TextualApp 骨架

改 `display.py`，把 `_TerminalDisplay` 改为 `_TextualDisplay`。

- `_start`：启动 Textual App（常驻）
- `_render(text)`：更新 Markdown widget
- `_stop`：停止 App
- 接口（`on_delta`/`on_display`/`on_flush`）不变

此步结束后：`python tests.py` 的 display 测试通过。

### 第 2 步：输入集成

改 `chat.py`：`input()` 替换为 Textual 输入框。

- agent 循环在 worker 线程运行
- 通过 `call_from_thread` 推送 token 到 UI
- 斜杠命令在输入框内处理
- Ctrl+C 绑定为 `stop_event.set()`

此步结束后：能正常对话，流式打字机效果正常。

### 第 3 步：清理

删除 Rich Live 相关代码，移除 `display.py` 中不再需要的 import。

### 第 4 步：回滚验证

在 Textual 版本上跑一轮完整对话，确认：
- 打字机逐字符渲染
- 代码块高亮正常
- 长内容滚动无重复
- `/new` `/model` `/help` 可用
- Ctrl+C 停止当前轮

## 风险

- Windows 终端对 Textual 的兼容性（已通过 `_test_textual.py` 验证）
- worker 线程的 `call_from_thread` 是 Textual 标准 API，有官方支持
