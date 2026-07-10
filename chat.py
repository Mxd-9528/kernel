
import signal
from types import SimpleNamespace

from llm import _default_model
from agent import agent, stop, emit
from history import load


def _handle_sigint(signum, frame):
    from agent import stop
    stop.set()


def chat(model=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令：/new /model /help。
    按 Ctrl+C 停止：当前轮走完后回到输入，不继续下轮。
    model: None 用默认（models.json 第一个）。
    """
    signal.signal(signal.SIGINT, _handle_sigint)

    model = model or _default_model()
    messages = load()  # 自动接续上次对话；无历史则 None
    if messages is None:
        from system import build_system
        messages = [{"role": "system", "content": build_system()}]
    while True:
        try:
            you = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if you == "exit":
            break

        # 斜杠命令：交给事件处理器
        if you.startswith("/"):
            state = SimpleNamespace(messages=messages or [], model=model)
            emit("on_command", you, state)
            model = state.model
            messages = state.messages
            continue

        # 自由文本：进入 agent
        stop.clear()
        state = SimpleNamespace(messages=messages or [], model=model)
        state = agent(you, state)
        messages = state.messages
        if stop.is_set():
            print("\n（已停止）")
            stop.clear()
