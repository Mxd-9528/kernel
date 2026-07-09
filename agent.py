"""事件系统 + 纯 agent（循环节奏，零业务填充）。"""
import re
import threading
from types import SimpleNamespace


_hooks = {}

def on(event):
    """注册事件处理器。"""
    def decorator(fn):
        _hooks.setdefault(event, []).append(fn)
        return fn
    return decorator

def emit(event, *args, **kwargs):
    """触发事件，依次调用所有已注册的处理器。"""
    for fn in _hooks.get(event, []):
        fn(*args, **kwargs)


# 协作式中断。业务处理器检查此标志，设置后停止下一轮。
stop = threading.Event()

_MAX_ITERS = 20

# 代码块检测正则——循环控制的一部分，不是业务。
_EXEC_PATTERN = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"


def agent(prompt, state=None, max_iters=_MAX_ITERS):
    """循环：发 → 追1 → 检查 → 追2 → 重复。业务填充通过事件注入。"""
    if state is None:
        state = SimpleNamespace(messages=[])
    state.messages.append({"role": "user", "content": prompt})

    for _ in range(max_iters):
        if stop.is_set():
            break

        emit("before_send", state)   # → compact.py
        emit("send", state)          # → llm.py：发请求 + 追1
        emit("after_assistant", state)

        reply = state.messages[-1]["content"]
        blocks = [m.strip() for m in re.findall(_EXEC_PATTERN, reply, re.DOTALL)]
        if not blocks:
            return state  # 纯文本 = 结束

        emit("execute", state)       # → runtime.py：执行 + 追2

    return state
