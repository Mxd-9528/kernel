from agent import on
from history import reset_history

_HELP = """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助
  exit           退出"""


@on("on_command")
def handle_command(cmd, state):
    if cmd == "/new":
        state.messages = reset_history()
        print("已开新对话。")
    elif cmd.startswith("/model"):
        from llm import _list_models, _default_model
        models = _list_models()
        name = cmd[len("/model"):].strip()
        if not name:
            print(f"当前模型：{state.model}。可选：{', '.join(models)}")
        elif name in models:
            state.model = name
            print(f"已切换到 {name}")
        else:
            print(f"未知模型 {name}。可选：{', '.join(models)}")
    elif cmd == "/help":
        print(_HELP)
    else:
        print(f"未知命令：{cmd}，输入 /help 查看所有可用命令")
