import re
import threading
from pathlib import Path

from call import call
from compact import compact
from history import save
from manifest import list_tools
from rich.console import Console
from rich.markdown import Markdown
from run import run
from skills import list_skills

# B 闭环：模型自己在持久内核里干活——回代码 → 执行 → 喂结果 → 再回代码 → 直到它说"做完了"。
# 代码块就是没预先写好的预置函数，执行和捕获走同一条路径，返回同一套三元组。

_MAX_ITERS = 20

# 中断协议（协作式，不打断 IPython 单元）：
#   stop.set()    外部要求停下（Ctrl+C / 命令切换）
#   stop.clear()  新任务开始前清零
#   stop.is_set() 循环边界检查
stop = threading.Event()

# 外层 <!EXEC>...</EXEC> 是真边界（代码里不会出现）；内层 ``` 顺着模型天性。
# re.DOTALL 让 . 匹配换行，否则多行代码会被吞掉只剩第一行。
_EXEC_PATTERN = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"


def _extract(text):
    """从模型回话里抠出所有 <!EXEC> 代码块，返回代码字符串列表。"""
    return [m.strip() for m in re.findall(_EXEC_PATTERN, text, re.DOTALL)]


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

        results = [run(b) for b in blocks]
        messages.append({"role": "user", "content": feedback(results)})
        save(messages)  # 步级存盘：环境反馈即落盘

    # 到达最大轮数或被 stop 打断
    return reply, messages
