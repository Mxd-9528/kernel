import re
import threading
from pathlib import Path

from background import run_with_timeout
from call import call
from compact import compact
from history import save
from manifest import list_tools
from rich.console import Console
from rich.markdown import Markdown
from skills import list_skills

# B 闭环：模型自己在持久内核里干活——回代码 → 执行 → 喂结果 → 再回代码 → 直到它说"做完了"。
# 代码块就是没预先写好的预置函数，返回 Python 原生类型；异常通过 raise 传递。

_MAX_ITERS = 20
_MAX_RUN_SECS = 60  # 单代码块硬超时秒数，超过则转后台由 task_status 查询

# 中断协议（协作式，不打断 IPython 单元）：
#   stop.set()    外部要求停下（Ctrl+C / 命令切换）
#   stop.clear()  新任务开始前清零
#   stop.is_set() 循环边界检查
stop = threading.Event()

# 外层 <!EXEC>...</EXEC> 是真边界（代码里不会出现）；内层 ``` 顺着模型天性。
# re.DOTALL 让 . 匹配换行，否则多行代码会被吞掉只剩第一行。
_EXEC_PATTERN = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"

# ANSI 转义序列清洗（IPython 输出可能带颜色码）
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _extract(text):
    """从模型回话里抠出所有 <!EXEC> 代码块，返回代码字符串列表。"""
    return [m.strip() for m in re.findall(_EXEC_PATTERN, text, re.DOTALL)]


def _run_cell(code):
    """在持久 IPython 内核里执行一个代码块。

    成功：返回表达式值（若有）或 stdout 字符串；无输出返回 None。
    失败：raise 原生异常（含完整 traceback）。
    """
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    sh = InteractiveShell.instance()
    from inject import inject
    inject(sh)

    with capture_output() as cap:
        r = sh.run_cell(code)

    stdout = _ANSI.sub("", cap.stdout)
    stderr = _ANSI.sub("", cap.stderr)

    if not r.success:
        # 把 stdout / stderr 附到异常上，feedback 能一并展示
        exc = r.error_in_exec
        exc._kernel_stdout = stdout  # type: ignore[attr-defined]
        exc._kernel_stderr = stderr  # type: ignore[attr-defined]
        raise exc

    # stderr 非空时通过 print 输出到 stdout 前面（合并流保持时序）
    if stderr.strip():
        stdout = stderr + stdout

    if r.result is not None:
        return r.result
    return stdout.strip() if stdout.strip() else None


def build_system():
    """组装完整系统提示词：prompt.txt + 预置函数清单 + 技能清单 + 可选 system_append.txt。"""
    here = Path(__file__).parent
    out = (here / "prompt.txt").read_text("utf-8") + \
          "\n\n# 预置函数（已注入命名空间，直接调用，无需 import）\n\n" + list_tools()
    sk = list_skills()
    if sk:
        out += "\n\n# 技能\n\n" + sk
    append_path = here / "system_append.txt"
    if append_path.exists():
        out += "\n\n" + append_path.read_text("utf-8")
    return out


def render(reply):
    """把模型回复渲染给人看（Markdown）。环境反馈不在这里打印。"""
    Console().print(Markdown(reply))


def feedback(results):
    """把代码块的执行结果拼成喂给模型的环境反馈文本。

    每项可能是任意 Python 对象或 BaseException。用 Python 内置 repr / traceback
    表达，不引入自造格式。
    """
    parts = ["[环境反馈]"]
    multi = len(results) > 1
    for i, r in enumerate(results):
        if multi:
            parts.append(f"\n--- 代码块 {i + 1} ---")
        if isinstance(r, BaseException):
            import traceback
            # 若异常带内核 stdout/stderr（_run_cell 附上的），先展示
            for attr in ("_kernel_stdout", "_kernel_stderr"):
                text = getattr(r, attr, "")
                if text and text.strip():
                    parts.append(text.rstrip())
            tb = "".join(traceback.format_exception(type(r), r, r.__traceback__))
            parts.append(tb.rstrip())
        elif r is None:
            parts.append("(无输出)")
        elif isinstance(r, str):
            parts.append(r if r else "(空字符串)")
        else:
            parts.append(repr(r))
    return "\n".join(parts)


def _execute_block(code):
    """执行一个代码块，返回结果或异常对象（不 raise 出去，让 feedback 分派）。

    - 正常完成：返回原生 Python 值（可能是 None）
    - 代码块内异常：返回该异常对象（含 traceback）
    - 超时（>_MAX_RUN_SECS 秒）：返回 TimeoutError（含 task_id 引导文本），任务继续在后台
    """
    result, error, task_id = run_with_timeout(_run_cell, _MAX_RUN_SECS, code)
    if task_id is not None:
        # 超时分支：任务已转后台，替换为含引导信息的 TimeoutError
        return TimeoutError(
            f"运行超过 {_MAX_RUN_SECS} 秒，已转为后台任务。task_id={task_id}\n"
            f"用 task_status(\"{task_id}\") 查状态，task_cancel(\"{task_id}\") 取消。"
        )
    if error is not None:
        # 代码块内 raise 出来的异常，原样返回让 feedback 用 traceback 展示
        return error
    return result


def agent(prompt, messages=None, model=None, max_iters=_MAX_ITERS):
    """启动模型自驱动执行循环。

    prompt: 本轮用户任务。
    messages: 跨轮历史列表（chat 持有并复用）。None 时新建一段带 system 的历史。
    model: models.json 里的模型名。None 用默认（json 第一个）。
    max_iters: 单轮最多跑几次执行循环，防止无限循环。
    """

    if messages is None:
        messages = [{"role": "system", "content": build_system()}]
    messages.append({"role": "user", "content": prompt})

    reply = ""
    for _ in range(max_iters):
        if stop.is_set():
            break  # chat 按了 Ctrl+C，回到输入
        messages = compact(messages, model=model)
        reply = call(messages, model)
        render(reply)
        messages.append({"role": "assistant", "content": reply})
        save(messages)  # 步级存盘：模型回复即落盘

        blocks = _extract(reply)
        if not blocks:
            return reply, messages  # 纯文本 = 模型收尾

        results = [_execute_block(b) for b in blocks]
        messages.append({"role": "user", "content": feedback(results)})
        save(messages)  # 步级存盘：环境反馈即落盘

    # 到达最大轮数或被 stop 打断
    return reply, messages
