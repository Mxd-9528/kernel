"""流式静默计数 + 完结一次性 Rich 渲染。不做增量 markdown——那条路是 bug 池。"""
import itertools
import re
import sys
import threading
import time

from .observer import BaseObserver
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

console = Console(theme=Theme({"markdown.code": "medium_purple", "markdown.h1": "white", "markdown.h2": "white", "markdown.h3": "white", "markdown.table_header": "white"}))
_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# 复用 runtime.py 的执行代码块正则，保证折叠与执行匹配同一组块
_EXEC_RE = re.compile(r"<EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>", re.DOTALL)

def _fold_exec_blocks(text):
    """把 <EXEC>...</EXEC> 代码块替换为折叠摘要代码块。"""
    def _replacer(m):
        code = m.group(1).strip()
        lines = code.splitlines()
        n = len(lines)
        preview = "(空)"
        for line in lines:
            s = line.strip()
            if s and not s.startswith("#"):
                preview = s
                break
        if preview == "(空)" and n > 0:
            preview = lines[0].strip()
        if len(preview) > 55:
            preview = preview[:55] + "..."
        preview = preview.replace("`", "'")
        if n == 1:
            return f"```\n{preview}\n```"
        return f"```\n代码块 · {n} 行 · {preview}\n```"
    return _EXEC_RE.sub(_replacer, text)


class _Spinner(BaseObserver):
    """流式期间刷 spinner 行；flush 时 Rich 一次性渲染累加正文。
    两阶段计数：thinking → content，label 与 tokens 各自独立。"""

    def __init__(self):
        self._buf = ""                       # 正文累积（仅 content）
        self._tokens = 0                     # 当前阶段 token 数
        self._label = "思考中"
        self._start = None                   # 当前阶段起始时刻
        self._thread = None
        self._stop = threading.Event()

    def _ensure_running(self):
        if self._thread is None:
            self._start = time.monotonic()
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def on_thinking(self, token):
        self._tokens += 1
        self._ensure_running()

    def on_delta(self, token):
        # 首个 content token：切阶段——归零计数、重置计时
        if self._label != "回复中":
            self._label = "回复中"
            self._tokens = 0
            self._start = time.monotonic()
        self._buf += token
        self._tokens += 1
        self._ensure_running()

    def _loop(self):
        for frame in itertools.cycle(_FRAMES):
            if self._stop.is_set():
                return
            elapsed = int(time.monotonic() - self._start)
            sys.stdout.write(
                f"\r\x1b[2m{frame} {self._label} · {self._tokens} tokens · {elapsed}s\x1b[0m\x1b[K"
            )
            sys.stdout.flush()
            self._stop.wait(0.1)

    def on_flush(self, text: str = ""):
        """停 spinner、清行、Rich 渲染正文。幂等。"""
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            self._thread = None
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
        if self._buf:
            folded = _fold_exec_blocks(self._buf)
            clean = folded.replace("<EXEC>", "").replace("</EXEC>", "")
            console.print(Markdown(clean))
        self._buf = ""
        self._tokens = 0
        self._label = "思考中"
        self._start = None

    def display_msg(self, content):
        """显示命令结果等非流式消息。"""
        if content:
            console.print(content)


spinner = _Spinner()
