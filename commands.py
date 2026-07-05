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
            builtin += "\n".join(f"  /{p.split('_')[0]:<14} {p.split('_')[1] if '_' in p else f'{p} 模式'}" for p in prompts)

    builtin += "\n  exit           退出"
    return builtin


def handle(cmd, model, messages):
    """处理斜杠命令。不是命令返回 handled=False。

    架构原则：只组装 prompt 字符串，不碰 messages 结构，
    messages 的组织完全由 agent() 主循环负责。
    """
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
            trigger = f"/{f.stem.split('_')[0]}"
            if cmd.startswith(trigger):
                import agent as agent_mod
                prompt = (Path(__file__).parent / "prompts" / f.name).read_text("utf-8")
                question = cmd[len(trigger):].strip() or "请执行对应任务"
                full_prompt = question + "\n\n执行以下约束：\n\n" + prompt
                agent_mod.clear_stop()
                result, new_messages = agent_mod.agent(full_prompt, messages, model)
                return new_messages, model, None, True

    # 未知命令
    return messages, model, f"未知命令：{cmd}，输入 /help 查看所有可用命令", True
