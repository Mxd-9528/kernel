"""斜杠命令处理器。

加新命令：在 prompts/ 下新建 xxx.txt，自动生成 /xxx 命令。
不需要改代码，零配置。
"""

from pathlib import Path


def help_text():
    """帮助文本，显示所有可用命令。"""
    builtin = """内置命令：
  /new           清空历史，开一段新对话
  /model <名>    切换模型，不带参数显示当前模型
  /help          显示此帮助"""

    # 自动扫描 prompts 目录
    prompt_dir = Path(__file__).parent / "prompts"
    if prompt_dir.exists():
        prompts = sorted([f.stem for f in prompt_dir.glob("*.txt")])
        if prompts:
            builtin += "\n\n提示词命令：\n"
            builtin += "\n".join(f"  /{p:<14} {p} 模式" for p in prompts)

    builtin += "\n  exit           退出"
    return builtin


def _run_prompt_mode(prompt_file, user_input, model):
    """运行一个提示词模式。"""
    prompt = (Path(__file__).parent / "prompts" / prompt_file).read_text("utf-8")
    import agent as agent_mod
    agent_mod._stop = False
    result, _ = agent_mod.agent(user_input, [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input},
    ], model)
    return result


def handle(cmd, model, messages):
    """处理斜杠命令。不是命令返回 handled=False。"""
    if not cmd.startswith("/"):
        return messages, model, None, False

    # 内置命令 /new
    if cmd == "/new":
        from history import save
        save([])
        return None, model, "已开新对话。", True

    # 内置命令 /model
    if cmd.startswith("/model"):
        from call import _models
        models = _models()
        name = cmd[len("/model"):].strip()
        if not name:
            return messages, model, f"当前模型：{model}。可选：{', '.join(models)}", True
        elif name in models:
            return messages, name, f"已切换到 {name}", True
        else:
            return messages, model, f"未知模型 {name}。可选：{', '.join(models)}", True

    # 内置命令 /help
    if cmd == "/help":
        return messages, model, help_text(), True

    # 自动扫描提示词命令
    prompt_dir = Path(__file__).parent / "prompts"
    if prompt_dir.exists():
        for f in prompt_dir.glob("*.txt"):
            trigger = f"/{f.stem}"
            if cmd.startswith(trigger):
                question = cmd[len(trigger):].strip() or "请执行对应任务"
                _run_prompt_mode(f.name, question, model)
                return messages, model, f"（{f.stem} 模式）", True

    # 未知命令
    return messages, model, f"未知命令：{cmd}，输入 /help 查看所有可用命令", True
