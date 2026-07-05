"""把机件和预置函数推进 IPython 持久内核的 user_ns——run 启动时注入一次。

唯一的「特权」是被导入持久内核这个动作本身；除此之外都是普通 Python，没有模块有特权。
预置函数的单一事实源是 tools/（manifest 扫描）；机件在下方 _MACHINES 显式列出。

面向接口编程：只 import 无下划线的接口模块（call/background/compact/run），实现在 _*.py 水线以下。
"""


def _names():
    import inspect  # 预注入：对象反查看源码是核心动作（inspect.getsourcelines(对象)→文件:行号）
    from agent import agent, build_system as build_system_prompt
    from call import call
    from chat import chat
    from compact import compact
    from history import save as save_history, load as load_history
    from manifest import list_tools, presets
    from result import Result, ListResult, DictResult
    from run import run
    from skills import list_skills
    import background

    machines = {
        "agent": agent,
        "background": background,
        "build_system_prompt": build_system_prompt,
        "call": call,
        "chat": chat,
        "compact": compact,
        "list_skills": list_skills,
        "list_tools": list_tools,
        "load_history": load_history,
        "run": run,
        "save_history": save_history,
        "Result": Result,
        "ListResult": ListResult,
        "DictResult": DictResult,
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
