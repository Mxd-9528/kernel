from .history import reset_history
from .llm import list_models

_HELP = """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助
  exit           退出"""


def handle(cmd, messages, model):
    if cmd == "/new":
        messages = reset_history()
        return messages, model, "已开新对话。"
    elif cmd.startswith("/model"):
        models = list_models()
        name = cmd[len("/model"):].strip()
        if not name:
            return messages, model, f"当前模型：{model}。可选：{', '.join(models)}"
        elif name in models:
            import json
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent.parent
            cfg_path = root / "models.json"
            data = json.loads(cfg_path.read_text("utf-8"))
            data["default"] = name
            cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return messages, name, f"已切换到 {name}"
        else:
            return messages, model, f"未知模型 {name}。可选：{', '.join(models)}"
    elif cmd == "/help":
        return messages, model, _HELP
    else:
        return messages, model, f"未知命令：{cmd}，输入 /help 查看所有可用命令"