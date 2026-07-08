import re
import threading

from _display import render_stream
from _llm import call as _call, stream_chat
from _runtime import _EXEC_PATTERN, _execute_block, feedback
from _system import build_system
from compact import compact
from history import save

# 自驱动循环：模型输出代码块，_execute_block 在持久内核中执行，返回原生 Python 值或异常，
# feedback 拼成文本喂回模型，直到模型输出纯文本（无 <!EXEC>）为止。

_MAX_ITERS = 20

# 中断协议（协作式，不打断 IPython 单元）
stop = threading.Event()


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
        try:
            reply = render_stream(stream_chat(messages, model))
        except Exception:
            from rich.console import Console
            from rich.markdown import Markdown
            Console().print("\n[流式失败，fallback 到普通调用]")
            reply = _call(messages, model)
            Console().print(Markdown(reply))
        messages.append({"role": "assistant", "content": reply})
        save(messages)  # 步级存盘：模型回复即落盘

        blocks = [m.strip() for m in re.findall(_EXEC_PATTERN, reply, re.DOTALL)]
        if not blocks:
            return reply, messages  # 纯文本 = 模型收尾

        results = [_execute_block(b) for b in blocks]
        messages.append({"role": "user", "content": feedback(results)})
        save(messages)  # 步级存盘：环境反馈即落盘

    return reply, messages
