# 热补丁实战：为 Agent 添加流式逐字渲染

> 持久内核不能重启，但改代码不需要重启——内核里开发，子进程里终审。

## 背景

原始路径：`call()` 一次性返回完整文本 → `Console().print(Markdown(reply))` 一次性渲染。要改成逐 token 到达就逐字渲染。

## 接缝选择

`agent.py` 两处接缝，都在模块命名空间内，改名字即生效：

| 接缝 | 原行为 | 改为 |
|------|--------|------|
| `agent.call` | 一次性返回完整文本 | 流式获取 + 实时渲染，返回完整文本 |
| `agent.Console` | 不感知渲染 | 检测已渲染则跳过重复打印 |

## 最终版：call_streaming

```python
import json, os, sys, time, urllib.request
from rich.live import Live
from rich.markdown import Markdown

def call_streaming(messages, model=None):
    cfg, key = _get_cfg(model)
    body = json.dumps({"model": cfg["model"], "messages": messages, "stream": True}).encode()
    req = urllib.request.Request(cfg["url"], data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)

    collected = ""
    live = Live(Markdown(""), refresh_per_second=60, screen=False, vertical_overflow="visible")
    live.start()
    try:
        for line_bytes in resp:
            line = line_bytes.decode().strip()
            if not line or not line.startswith("data: "): continue
            data_str = line[6:]
            if data_str == "[DONE]": break
            try: chunk = json.loads(data_str)
            except json.JSONDecodeError: continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if delta.get("reasoning_content"): continue   # 思维链静默跳过
            content = delta.get("content", "")
            if content:
                for ch in content:          # 逐字 drip-feed
                    collected += ch
                    live.update(Markdown(collected))
                    time.sleep(0.008)
    except Exception:
        live.stop()
        from _call import call as _original_call
        return _original_call(messages, model)
    finally:
        live.stop()
    return collected
```

## 透镜夹层

```python
import agent as agent_mod

class _StreamingConsoleProxy:
    def __call__(self, *args, **kwargs):
        return _StreamingConsoleInstance(*args, **kwargs)

class _StreamingConsoleInstance:
    def print(self, *args, **kwargs):
        if args and isinstance(args[0], Markdown):
            rendered = getattr(agent_mod, "_streamed_reply", None)
            if rendered is not None and rendered == args[0].markup:
                del agent_mod._streamed_reply
                return  # 已流式渲染，跳过
        from rich.console import Console as _OriginalConsole
        _OriginalConsole().print(*args, **kwargs)

def _streaming_call(messages, model=None):
    result = call_streaming(messages, model)
    agent_mod._streamed_reply = result
    return result

agent_mod.call = _streaming_call
agent_mod.Console = _StreamingConsoleProxy()
```

## 迭代中的三个关键修复

### 1. 消除闪烁：`screen=False`

`Live` 默认 `screen=True` 使用交替缓冲区，每次 `update()` 整屏切换，导致闪烁。改为 `screen=False` 原地刷新，只有变化区域重绘。

### 2. 平滑逐字：char-level drip-feed + 高刷新率

SSE 返回的 token 通常是一段文字，直接 `live.update(Markdown(collected))` 会整段跳出来。改为遍历 token 中每个字符，逐个追加并 `live.update()`，中间 `time.sleep(0.008)`。配合 `refresh_per_second=60`，肉眼看到的就是逐字流畅打出。

### 3. 思维链：静默跳过

思维链输出与 Live 渲染区域争夺终端控制权，导致位置错乱、样式丢失。最终方案：`reasoning_content` delta 直接 `continue` 跳过，不占终端。模型内部推理仍进行，但不干扰用户可见的流式输出。

## 设计精髓

```
agent.agent() 源码一行未改
    │
    ├─ reply = call(...)  ← 实际调用 _streaming_call
    │     └─ HTTP SSE → 逐字符 Live.update() → 返回完整 reply
    │
    └─ Console().print(Markdown(reply))  ← Console 被代理
          └─ 检测 reply == _streamed_reply → 跳过
```

- **接口不变**：`call()` 返回值仍是完整字符串，`agent.agent()` 后续逻辑（`messages.append`、`save`）不受影响
- **透明代理**：`Console` 代理类检测 `_streamed_reply` 标记，已渲染的跳过，其余原样转发
- **不修改源码**：两个热绑定换了模块命名空间里的名字，`agent.py` 磁盘文件一字不改
- **安全 fallback**：流式异常时自动回退到原始 `call()`，对话不中断