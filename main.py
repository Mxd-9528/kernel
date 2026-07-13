'''入口：加载所有模块，显式注册事件处理器，启动对话。'''
from agent import on, EVENT_THINKING, EVENT_DISPLAY, EVENT_FLUSH,     EVENT_BEFORE_SEND, EVENT_SAVE, EVENT_DISPLAY_MSG
from display import on_thinking, on_delta, on_flush, on_display
from history import on_save
from compact import before_send
from chat import chat

# ── 显式注册事件处理器（非 import 副作用） ──────────────────────────

on(EVENT_THINKING)(on_thinking)
on(EVENT_DISPLAY)(on_delta)
on(EVENT_FLUSH)(on_flush)
on(EVENT_DISPLAY_MSG)(on_display)
on(EVENT_BEFORE_SEND)(before_send)
on(EVENT_SAVE)(on_save)

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model)
