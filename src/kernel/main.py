'''入口：组合观察者，启动对话。'''
from .observer import CompositeObserver
from .display import spinner
from .compact import observer as compact_observer
from .history import observer as history_observer
from .chat import chat

# ── 显式组合观察者（非 import 副作用） ──────────────────────────

observer = CompositeObserver([spinner, compact_observer, history_observer])


def main():
    import sys
    import threading

    args = [a for a in sys.argv[1:] if a != "--web"]
    model = args[0] if args else None

    if "--web" in sys.argv:
        from .web.observer import WebSocketObserver
        from .web.server import serve

        ws_obs = WebSocketObserver()
        web_observer = CompositeObserver([ws_obs, compact_observer, history_observer])

        t = threading.Thread(target=serve, args=(ws_obs,), daemon=True)
        t.start()

        # 自动打开浏览器（优先 VS Code 内置）
        import os as _os
        import subprocess as _sp
        url = "http://localhost:8765"
        print(f"  → 浏览器打开 {url}")
        try:
            _sp.run(f"code --open-url {url}", shell=True, timeout=5)
        except Exception:
            _os.startfile(url)

        chat(model=model, observer=web_observer,
             input_source=lambda: ws_obs.input_queue.get())
    else:
        chat(model=model, observer=observer)


if __name__ == "__main__":
    main()
