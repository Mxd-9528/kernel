
import signal


def _handle_sigint(signum, frame):
    import agent as agent_mod
    agent_mod.stop.set()


_HELP = """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助
  exit           退出"""


def chat(model=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令：/new /model /help。
    按 Ctrl+C 停止：当前轮走完后回到输入，不继续下轮。
    model: None 用默认（models.json 第一个）。
    """
    signal.signal(signal.SIGINT, _handle_sigint)
    import agent as agent_mod
    from call import default_model, _models
    from history import save, load

    model = model or default_model()
    messages = load()  # 自动接续上次对话；无历史则 None
    while True:
        try:
            you = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if you == "exit":
            break

        # 斜杠命令：直接改本地 REPL 状态
        if you == "/new":
            save([])
            messages = None
            print("已开新对话。")
            continue
        if you.startswith("/model"):
            models = _models()
            name = you[len("/model"):].strip()
            if not name:
                print(f"当前模型：{model}。可选：{', '.join(models)}")
            elif name in models:
                model = name
                print(f"已切换到 {name}")
            else:
                print(f"未知模型 {name}。可选：{', '.join(models)}")
            continue
        if you == "/help":
            print(_HELP)
            continue
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
