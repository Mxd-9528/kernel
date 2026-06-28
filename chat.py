
import signal


def _handle_sigint(signum, frame):
    import agent as agent_mod
    agent_mod._stop = True


def chat(model=None):
    """连续对话——你一句、它干完、回你、再等你下一句。历史跨轮保留、跨启动接续。

    输入 exit 退出。斜杠命令：
      /model <名>    切换模型（名取自 models.json）
      /new           清空历史，开一段新对话
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
        if you == "/new":
            messages = None
            save([])
            print("已开新对话。")
            continue
        if you.startswith("/model"):
            models = _models()
            name = you[len("/model"):].strip()
            if not name:
                print(f"当前模型：{model}。可选：{', '.join(models)}")
            elif name in models:
                model = name
                print(f"已切换到 {model}")
            else:
                print(f"未知模型 {name}。可选：{', '.join(models)}")
            continue
        agent_mod._stop = False
        result, messages = agent_mod.agent(you, messages, model)
        if agent_mod._stop:
            print("\n（已停止）")
            agent_mod._stop = False


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model)
