"""入口：启动对话。"""
from .display import spinner
from .chat import chat


def main():
    import sys
    import threading

    args = [a for a in sys.argv[1:] if a != "--web"]
    model = args[0] if args else None

    if "--web" in sys.argv:
        from .web.observer import WebSocketObserver
        from .web.server import serve

        ws_obs = WebSocketObserver()

        t = threading.Thread(target=serve, args=(ws_obs,), daemon=True)
        t.start()

        # 自动打开浏览器（优先 VS Code 内置）
        import os as _os
        import subprocess as _sp
        url = "http://localhost:8765"
        print(f"  \u2192 \u6d4f\u89c8\u5668\u6253\u5f00 {url}")
        try:
            _sp.run(f"code --open-url {url}", shell=True, timeout=5)
        except Exception:
            _os.startfile(url)

        chat(model=model, observer=ws_obs,
             input_source=lambda: ws_obs.input_queue.get(),
             interrupt_event=ws_obs.interrupt_event)
    else:
        chat(model=model, observer=spinner)


if __name__ == "__main__":
    main()
