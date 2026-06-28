"""把机件和预置函数推进 IPython 持久内核的 user_ns——run 启动时注入一次。

唯一的「特权」是被导入持久内核这个动作本身；除此之外都是普通 Python，没有模块有特权。
预置函数的单一事实源是 tools/（manifest 扫描），机件从 load 取。
"""


def _names():
    import inspect  # 预注入：对象反查看源码是核心动作（inspect.getsourcelines(对象)→文件:行号）
    import load  # 机件：延迟导入打破 load→inject 循环
    from manifest import presets  # 预置函数：tools/ 单一事实源

    names = {n: getattr(load, n) for n in dir(load) if not n.startswith("_")}
    names.update(presets())  # tools/ 里的预置函数，加工具只动 tools/，这里和 prompt 都自动跟上
    names["load"] = load
    names["inspect"] = inspect  # dict 合并不用 |（3.9+），兼容 3.8
    return names


def inject(shell):
    """首轮把机件和预置函数推进 user_ns。已注入则跳过——不覆盖模型在内核里的重绑定。

    每轮重 push 会抹掉模型对预置函数的改进，毁掉持久内核"跨轮保留"的核心优势。
    所以只注入一次：用真实预置函数名做哨兵，比单独的标记位健壮。
    （代价：会话中新加 tools/ 文件需重启 chat 才生效——加工具本就改文件，可接受。）
    """
    if "read" in shell.user_ns:  # 已注入过
        return
    shell.push(_names())
