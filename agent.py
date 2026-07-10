"""事件系统 + 纯 agent（循环节奏，零业务填充）。"""
import threading
from types import SimpleNamespace

import llm
import runtime


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


_MAX_ITERS = 20


def agent(prompt, state=None, max_iters=_MAX_ITERS):
    """循环：请求 → 追1 → 提取代码块 → 执行 → 追2 → 下一轮。"""
    if state is None:
        state = SimpleNamespace(messages=[])
    if not getattr(state, "stop", None):
        state.stop = threading.Event()
    state.messages.append({"role": "user", "content": prompt})

    for _ in range(max_iters):
        if state.stop.is_set():
            break

        emit("before_send", state)   # → compact.py
        model = getattr(state, "model", None)
        try:
            reply = ""
            for token in llm.stream_chat(state.messages, model):
                reply += token
                emit("display_delta", token)
            emit("display_flush")
        except Exception as e:
            emit("display_flush")
            reply = f"LLM 请求失败: {e}"
        state.messages.append({"role": "assistant", "content": reply})
        emit("save", state.messages)

        blocks = runtime.extract_blocks(reply)
        if not blocks:
            return state  # 纯文本 = 结束

        results = runtime.execute_blocks(blocks)
        state.messages.append({"role": "user", "content": runtime.feedback(results)})
        emit("save", state.messages)

    return state
