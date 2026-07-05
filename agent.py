from pathlib import Path

from call import call
from compact import should_compact, compact
from extract import extract
from history import save
from rich.console import Console
from rich.markdown import Markdown
from run import run

# B 闭环：模型自己在持久内核里干活——回代码 → 执行 → 喂结果 → 再回代码 → 直到它说"做完了"。
# 代码块就是没预先写好的预置函数，执行和捕获走同一条路径，返回同一套三元组。

_MAX_ITERS = 20

# 中断协议（协作式，不打断 IPython 单元）：
#   request_stop() → 外部要求停下（Ctrl+C / 命令切换）
#   clear_stop()   → 新任务开始前清零
#   should_stop()  → 循环边界检查
# 内部标志用 _stop，外部只调三个函数——不摸变量。
_stop = False


def request_stop():
    global _stop
    _stop = True


def clear_stop():
    global _stop
    _stop = False


def should_stop():
    return _stop


# 系统提示组装逻辑已移至 system_prompt.py，避免本文件膨胀
from system_prompt import build as build_system


def render(reply):
    """把模型回复渲染给人看（Markdown）。环境反馈不在这里打印。"""
    Console().print(Markdown(reply))


def feedback(results):
    """把代码块的三元组结果拼成喂给模型的环境反馈文本。repr 原样转达 Body+error+facts。"""
    parts = ["[环境反馈]"]
    multi = len(results) > 1
    for i, r in enumerate(results):
        if multi:
            parts.append(f"\n--- 代码块 {i + 1} ---")
        parts.append(repr(r) if repr(r) else "(无输出)")
    return "\n".join(parts)


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
        if _stop:
            break  # chat 按了 Ctrl+C，回到输入
        if should_compact(messages):
            messages = compact(messages, model=model)
        reply = call(messages, model)
        render(reply)
        messages.append({"role": "assistant", "content": reply})
        save(messages)  # 步级存盘：模型回复即落盘

        blocks = extract(reply)
        if not blocks:
            return reply, messages  # 纯文本 = 模型收尾

        results = [run(b) for b in blocks]
        messages.append({"role": "user", "content": feedback(results)})
        save(messages)  # 步级存盘：环境反馈即落盘

    # 到达最大轮数或被 _stop 打断
    return reply, messages
