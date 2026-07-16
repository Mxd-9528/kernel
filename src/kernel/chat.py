
import signal
import threading

from . import commands
from .llm import default_model
from .agent import agent
from .history import load

# signal handler 通过此 cell 访问当前轮次的 stop_event
_current_stop = None


def _handle_sigint(signum, frame):
    if _current_stop is not None:
        _current_stop.set()


def chat(messages=None, *, model=None, observer=None, input_source=None,
         interrupt_event=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令：/new /model /help。
    按 Ctrl+C 停止：当前轮走完后回到输入，不继续下轮。
    model: None 用默认（models.json 第一个）。
    observer: None 时静默（无显示、无存盘、无压缩）。
    input_source: None 时用终端 input()；否则调用 input_source() 获取下一行输入。
    interrupt_event: None 或 threading.Event。Web 模式下，server 收到 interrupt
                    消息后设置此 Event；daemon 线程检测到后桥接到 stop_event。
    """
    global _current_stop
    signal.signal(signal.SIGINT, _handle_sigint)

    model = model or default_model()
    if messages is None:
        messages = load()
    if messages is None:
        from .system import build_system
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

        # Web 中断：daemon 线程监听 interrupt_event → 桥接 stop_event
        interrupt_thread = None
        if interrupt_event is not None:
            interrupt_event.clear()
            interrupt_thread = threading.Thread(
                target=lambda: (interrupt_event.wait(), stop_event.set()),
                daemon=True,
            )
            interrupt_thread.start()

        messages = agent(you, messages=messages, model=model,
                         stop_event=stop_event, observer=observer)
        _current_stop = None
        if stop_event.is_set():
            print("\n（已停止）")
