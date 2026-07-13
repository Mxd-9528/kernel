from agent import emit, EVENT_DISPLAY_MSG
from history import reset_history
from llm import list_models, default_model

_HELP = """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助
  exit           退出"""


def handle(cmd, messages, model):
    if cmd == "/new":
        messages = reset_history()
        emit(EVENT_DISPLAY_MSG, "已开新对话。")
    elif cmd.startswith("/model"):
        models = list_models()
        name = cmd[len("/model"):].strip()
        if not name:
            emit(EVENT_DISPLAY_MSG, f"当前模型：{model}。可选：{', '.join(models)}")
        elif name in models:
            model = name
            emit(EVENT_DISPLAY_MSG, f"已切换到 {model}")
        else:
            emit(EVENT_DISPLAY_MSG, f"未知模型 {name}。可选：{', '.join(models)}")
    elif cmd == "/help":
        emit(EVENT_DISPLAY_MSG, _HELP)
    else:
        emit(EVENT_DISPLAY_MSG, f"未知命令：{cmd}，输入 /help 查看所有可用命令")
    return messages, model