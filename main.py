'''入口：组合观察者，启动对话。'''
from observer import CompositeObserver
from display import spinner
from compact import observer as compact_observer
from history import observer as history_observer
from chat import chat

# ── 显式组合观察者（非 import 副作用） ──────────────────────────

observer = CompositeObserver([spinner, compact_observer, history_observer])

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model, observer=observer)
