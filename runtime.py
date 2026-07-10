import re
import threading
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output

from inject import inject

_MAX_RUN_SECS = 60  # 单代码块硬超时秒数，超过则放弃等待、抛 TimeoutError（防止代码块永久阻塞卡住循环）

# 外层 <!EXEC>...</EXEC> 是真边界（代码里不会出现）；内层 ``` 顺着模型天性。
_EXEC_PATTERN = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# feedback 层的字符截断：防止大 read / bash 输出爆上下文
# 40/20/40 三段策略：头 40% + 中 20% + 尾 40%——中间 20% 刻意保留，
# 因为长日志的中间往往有关键信号（如 pip 的进度转折、traceback 的具体错误行、
# diff 的真实冲突位置）。头尾截断会丢这些。
_MAX_FEEDBACK_CHARS = 20000


def _run_cell(code):
    """在持久 IPython 内核里执行一个代码块。

    成功：返回表达式值（若有）或 stdout 字符串；无输出返回 None。
    失败：raise 原生异常（含完整 traceback）。
    """
    sh = InteractiveShell.instance()
    inject(sh)

    with capture_output() as cap:
        r = sh.run_cell(code)

    stdout = _ANSI.sub("", cap.stdout)
    stderr = _ANSI.sub("", cap.stderr)

    if not r.success:
        # IPython 语义：语法错误在 error_before_exec，运行时错误在 error_in_exec，两者互斥
        exc = r.error_before_exec or r.error_in_exec
        # 把 stdout / stderr 附到异常上，feedback 能一并展示
        exc._kernel_stdout = stdout  # type: ignore[attr-defined]
        exc._kernel_stderr = stderr  # type: ignore[attr-defined]
        raise exc

    # stderr 非空时前置到 stdout（字符串拼接近似合并流；IPython 分开采集，真实时序不可独立恢复）
    if stderr.strip():
        stdout = stderr + stdout

    if r.result is not None:
        return r.result
    return stdout.strip() if stdout.strip() else None


def _truncate(text):
    """超过 _MAX_FEEDBACK_CHARS 时按 40/20/40 三段保留。"""
    if len(text) <= _MAX_FEEDBACK_CHARS:
        return text
    head_n = int(_MAX_FEEDBACK_CHARS * 0.4)
    middle_n = int(_MAX_FEEDBACK_CHARS * 0.2)
    tail_n = _MAX_FEEDBACK_CHARS - head_n - middle_n
    middle_start = (len(text) - middle_n) // 2
    return (
        f"{text[:head_n]}\n"
        f"\n[... 截断 {len(text) - _MAX_FEEDBACK_CHARS:,} 字符，保留头/中/尾各 40%/20%/40% ...]\n\n"
        f"{text[middle_start:middle_start + middle_n]}\n"
        f"\n[... 截断继续 ...]\n\n"
        f"{text[-tail_n:]}"
    )


def feedback(results):
    """把代码块的执行结果拼成喂给模型的环境反馈文本。

    每项可能是任意 Python 对象或 BaseException。用 Python 内置 repr / traceback
    表达，不引入自造格式。超过 _MAX_FEEDBACK_CHARS 字符的输出自动 40/20/40 三段截断。
    """
    parts = ["[环境反馈]"]
    multi = len(results) > 1
    for i, r in enumerate(results):
        if multi:
            parts.append(f"\n--- 代码块 {i + 1} ---")
        if isinstance(r, BaseException):
            import traceback
            for attr in ("_kernel_stdout", "_kernel_stderr"):
                text = getattr(r, attr, "")
                if text and text.strip():
                    parts.append(_truncate(text.rstrip()))
            tb = "".join(traceback.format_exception(type(r), r, r.__traceback__))
            parts.append(_truncate(tb.rstrip()))
        elif r is None:
            parts.append("(无输出)")
        elif isinstance(r, str):
            parts.append(_truncate(r) if r else "(空字符串)")
        else:
            parts.append(_truncate(repr(r)))
    return "\n".join(parts)


def _execute_block(code):
    """执行一个代码块，返回结果或异常对象（不 raise 出去，让 feedback 分派）。

    超时保护：代码块最多跑 _MAX_RUN_SECS 秒；超过则放弃等待、返回 TimeoutError。
    daemon 线程：底层线程随 kernel 退出而清理；不做"转后台"任务管理——
    模型想让某个函数在后台跑，自己用 threading.Thread + daemon=True 或 tools/bg_start。
    """
    result = [None]
    error = [None]

    def _worker():
        try:
            result[0] = _run_cell(code)
        except BaseException as e:
            error[0] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=_MAX_RUN_SECS)
    if t.is_alive():
        return TimeoutError(f"代码块超过 {_MAX_RUN_SECS} 秒未完成，agent 放弃等待。若需长任务，用 bg_start 显式起后台。")
    return error[0] if error[0] is not None else result[0]


def extract_blocks(reply):
    """从回复中提取代码块，返回去壳后的代码字符串列表。"""
    return [m.strip() for m in re.findall(_EXEC_PATTERN, reply, re.DOTALL)]


def execute_blocks(blocks):
    """执行代码块列表，返回结果列表。"""
    return [_execute_block(b) for b in blocks]
