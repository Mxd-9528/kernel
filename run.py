import re

# 在持久内核里执行代码块，捕获 Python 原生反馈，返回三元组 Result。
# 代码块就是没预先写好的预置函数——同一条执行路径，同一套反馈接口。
# 成功静默：Body 是语义主值（表达式值/输出），.error=None。
# 失败喧哗：.error 承载代码块自身的原生异常对象；stdout 含 traceback，保真进 .facts。

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TIMEOUT = 60  # 单代码块超时秒数，超时转后台，不中断执行


def _run_cell(code):
    """实际执行代码块的内部函数，被线程池包装。"""
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    from result import Result

    sh = InteractiveShell.instance()
    from inject import inject

    inject(sh)
    with capture_output() as cap:
        r = sh.run_cell(code)

    stdout = _ANSI.sub("", cap.stdout)
    stderr = _ANSI.sub("", cap.stderr)

    if not r.success:
        facts = {"error": r.error_in_exec, "stdout": stdout}
        if stderr.strip():
            facts["stderr"] = stderr
        return Result("", **facts)

    from result import ListResult, DictResult

    if isinstance(r.result, (Result, ListResult, DictResult)):
        return r.result

    body = repr(r.result) if r.result is not None else stdout.strip()
    facts = {"error": None}
    if stderr.strip():
        facts["stderr"] = stderr
    return Result(body, **facts)


def run(code):
    from background_contract import run_with_timeout
    from result import Result

    result, timeout_error, task_id = run_with_timeout(_run_cell, _TIMEOUT, code)

    if timeout_error is not None:
        return Result(
            f"运行超过 {_TIMEOUT} 秒，已转为后台任务。\n"
            f"任务 ID: {task_id}\n"
            f"用 task_status(\"{task_id}\") 查状态，task_cancel(\"{task_id}\") 取消",
            error=timeout_error,
            task_id=task_id,
            status="background",
        )

    return result