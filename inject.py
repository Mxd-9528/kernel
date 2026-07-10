"""把机件和预置函数推进 IPython 持久内核的 user_ns——首次执行时注入一次。

唯一的"特权"是被导入持久内核这个动作本身；除此之外都是普通 Python。
预置函数的单一事实源是 tools/（manifest 扫描）；机件在下方显式列出。
"""


def _names():
    import inspect  # 预注入：对象反查看源码是核心动作（inspect.getsourcelines(对象)→文件:行号）
    from agent import agent
    from system import build_system as build_system_prompt
    from system import list_tools, list_skills, presets
    from chat import chat
    from compact import compact
    from history import save as save_history, load as load_history

    machines = {
        "agent": agent,
        "build_system_prompt": build_system_prompt,
        "chat": chat,
        "compact": compact,
        "list_skills": list_skills,
        "list_tools": list_tools,
        "load_history": load_history,
        "save_history": save_history,
        "inspect": inspect,
    }
    machines.update(dict(presets()))  # tools/ 里的预置函数，加工具只动 tools/，这里和 prompt 都自动跟上
    return machines


def inject(shell):
    """首轮把机件和预置函数推进 user_ns。已注入则跳过——不覆盖模型在内核里的重绑定。

    每轮重 push 会抹掉模型对预置函数的改进，毁掉持久内核"跨轮保留"的核心优势。
    专属哨兵挂在 shell 上，不依赖任何工具名——工具改名/删除也不会静默重注入。
    （代价：会话中新加 tools/ 文件需重启 chat 才生效——加工具本就改文件，可接受。）
    """
    if getattr(shell, "_kernel_injected", False):
        return
    shell.push(_names())
    shell._kernel_injected = True
