
import signal


def _handle_sigint(signum, frame):
    import agent as agent_mod
    agent_mod.stop.set()


def chat(model=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令见 commands.py。
    按 Ctrl+C 停止：当前轮走完后回到输入，不继续下轮。
    model: None 用默认（models.json 第一个）。
    """
    signal.signal(signal.SIGINT, _handle_sigint)
    import agent as agent_mod
    from call import default_model
    from commands import handle_config
    from history import load

    model = model or default_model()
    messages = load()  # 自动接续上次对话；无历史则 None
    while True:
        try:
            you = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if you == "exit":
            break

        # 配置命令：只改 REPL 状态
        cfg = handle_config(you, model, messages)
        if cfg is not None:
            messages, model, resp = cfg
            if resp:
                print(resp)
            continue

        # 未知斜杠命令：兜底提示，不发给 agent 浪费调用
        if you.startswith("/"):
            print(f"未知命令：{you}，输入 /help 查看所有可用命令")
            continue

        # 自由文本：进入 agent
        agent_mod.stop.clear()
        result, messages = agent_mod.agent(you, messages, model)
        if agent_mod.stop.is_set():
            print("\n（已停止）")
            agent_mod.stop.clear()


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model)
