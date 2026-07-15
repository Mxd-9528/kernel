# CLAUDE.md

项目概述见 [CONTEXT.md](CONTEXT.md)；人类入门见 [README.md](README.md)；设计原则见 [PRINCIPLES.md](PRINCIPLES.md)。

## 架构骨架

核心是 `agent.py` 的决策-执行-观察循环。Observer 协议（`on_thinking`/`on_delta`/`on_flush`/`before_send`/`save`/`display_msg`）是循环身上的钩子，非架构骨架。main.py 显式注册，新增消费者不修改注册表。

```
while True:                     # 决策-执行-观察 循环
    before_send  → compact      # 上下文压缩
    stream_model → display      # 模型输出 + 流式渲染
    has_code()?  → 终止         # 纯文本 = 停止
    execute_code → runtime      # 代码执行
    save         → history      # 持久化
```

斜杠命令由 `commands.handle()` 直接处理，在 `chat.py` 的外层循环中触发，不经过 agent 循环。

## 不读代码就不知道的

- 预置函数是预加载进 IPython `user_ns` 的普通 Python 函数，**不是** function calling 工具。
- `tools/` 与 `skills/*/SKILL.md` 通过文件系统扫描自动发现，新增能力仅需创建文件，无需注册。
- Python 标准库一行代码可完成的操作不封装为预置函数。

## 命令

```bash
pip install -e .            # 安装依赖（项目根目录）
ma                          # 启动对话（CLI 入口）
ma --web                    # 启动对话 + WebSocket 前端
python -m kernel            # 等价于 ma
python -m pytest tests/     # 运行全部测试
ruff check src/ tests/      # 代码检查
```

对话内命令：`exit` 退出；`/new` 清空历史；`/model <名>` 切换模型。命令显示通过 `display_msg` 通知输出。
