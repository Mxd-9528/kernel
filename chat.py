
import signal
import threading

import commands
import sys
from llm import default_model
from agent import agent
from history import load

# signal handler 通过此 cell 访问当前轮次的 stop_event
_current_stop = None


def _handle_sigint(signum, frame):
    if _current_stop is not None:
        _current_stop.set()


def chat(messages=None, *, model=None, observer=None, input_source=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令：/new /model /help。
    按 Ctrl+C 停止：当前轮走完后回到输入，不继续下轮。
    model: None 用默认（models.json 第一个）。
    observer: None 时静默（无显示、无存盘、无压缩）。
    input_source: None 时用终端 input()；否则调用 input_source() 获取下一行输入。
    """
    global _current_stop
    signal.signal(signal.SIGINT, _handle_sigint)

    model = model or default_model()
    if messages is None:
        messages = load()
    if messages is None:
        from system import build_system
        messages = [{"role": "system", "content": build_system()}]

    _get_input = input_source or (lambda: input("> "))

    while True:
        try:
            you = _get_input()
        except (EOFError, KeyboardInterrupt):
            break
        if you is None or you == "exit":
            break

        # 斜杠命令：直接调用
        if you.startswith("/"):
            messages = messages or []
            messages, model, display_msg = commands.handle(you, messages, model)
            if display_msg and observer:
                observer.display_msg(display_msg)
            continue

        # 自由文本：进入 agent
        stop_event = threading.Event()
        _current_stop = stop_event
        messages = agent(you, messages=messages, model=model, stop_event=stop_event, observer=observer)
        _current_stop = None
        if stop_event.is_set():
            print("\n（已停止）")
