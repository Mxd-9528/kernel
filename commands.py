"""斜杠命令：处理只改 REPL 状态的配置命令（/new /model /help）。

handle_config(cmd, model, messages) 匹配则返回 (新 messages, 新 model, 响应文本)，否则 None。
不调用 agent，只改本地状态。
"""

from pathlib import Path


def help_text():
    """帮助文本，显示所有可用命令。"""
    return """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助
  exit           退出"""


def handle_config(cmd, model, messages):
    if cmd == "/new":
        from history import save
        save([])
        return None, model, "已开新对话。"

    if cmd.startswith("/model"):
        from call import _models
        models = _models()
        name = cmd[len("/model"):].strip()
        if not name:
            return messages, model, f"当前模型：{model}。可选：{', '.join(models)}"
        if name in models:
            return messages, name, f"已切换到 {name}"
        return messages, model, f"未知模型 {name}。可选：{', '.join(models)}"

    if cmd == "/help":
        return messages, model, help_text()

    return None
