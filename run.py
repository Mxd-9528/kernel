import re

# 在持久内核里执行代码块，捕获 Python 原生反馈，返回三元组 Result。
# 代码块就是没预先写好的预置函数——同一条执行路径，同一套反馈接口。
# 成功静默：Body 是语义主值（表达式值/输出），.error=None。
# 失败喧哗：.error 承载代码块自身的原生异常对象；stdout 含 traceback，保真进 .facts。

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run(code):
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    from result import Result

    sh = InteractiveShell.instance()  # 单例 = 持久内核，变量跨轮保留
    from inject import inject
    inject(sh)  # 首轮把预置函数推进 user_ns；已注入则跳过，不覆盖模型的重绑定（保住跨轮持久）
    with capture_output() as cap:
        r = sh.run_cell(code)

    stdout = _ANSI.sub("", cap.stdout)  # 去 ANSI 色噪声，内容保真
    stderr = _ANSI.sub("", cap.stderr)

    if not r.success:
        # 失败喧哗：异常对象进 .error；stdout（traceback）是唯一诊断载体，保真进 .facts
        facts = {"error": r.error_in_exec, "stdout": stdout}
        if stderr.strip():
            facts["stderr"] = stderr
        return Result("", **facts)

    # 表达式值已是三元组（如预置函数返回）→ 原样返回，不重包不压扁
    from result import ListResult, DictResult
    if isinstance(r.result, (Result, ListResult, DictResult)):
        return r.result

    # 成功静默：表达式值优先，否则 stdout。已在 Body 里的不重复塞 facts；空值不塞
    body = repr(r.result) if r.result is not None else stdout.strip()
    facts = {"error": None}
    if stderr.strip():
        facts["stderr"] = stderr
    return Result(body, **facts)