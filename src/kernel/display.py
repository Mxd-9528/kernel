"""终端传输适配器：从 JSON-RPC 队列消费 dict → Rich 渲染。

终端是协议的第二个消费者，与 web/server.py 对称：
  agent → ProtocolObserver 入队 → TerminalRenderer 消费 → Rich 渲染
两个适配器共用同一套 5 种 JSON-RPC dict，验证协议与显示层解耦。
不做增量 markdown——那条路是 bug 池，flush 时一次性渲染。
"""
import itertools
import re
import sys
import threading
import time
from queue import Empty, Queue

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


class TerminalRenderer:
    """终端传输适配器：从 messages 队列消费 JSON-RPC dict → Rich 渲染。

    前置条件：messages 是 queue.Queue，元素为合法 JSON-RPC 2.0 notification dict
    后置条件：
      - run() 阻塞消费队列直到 stop()：期间刷 spinner 帧、按 method 分发
      - _handle(msg) 纯同步处理单条 dict，便于测试
    不变量：流式期间只刷 spinner；flush 时一次性 Rich 渲染，之后状态复位。
    两阶段计数：thinking → content，label 与 tokens 各自独立。

    与 web/server.py 对称——同一套 JSON-RPC dict，各自的传输/渲染方式。
    """

    def __init__(self, messages: Queue):
        self.messages = messages
        self._buf = ""                       # 正文累积（仅 content）
        self._tokens = 0                     # 当前阶段 token 数
        self._label = "思考中"
        self._start = None                   # 当前阶段起始时刻
        self._streaming = False              # 是否正在刷 spinner
        self._stop = threading.Event()

    # ── 队列消费循环（传输） ──────────────────────────────
    def run(self):
        """阻塞消费队列：有 dict 就处理，超时则刷 spinner 帧。stop() 后退出。"""
        for frame in itertools.cycle(_FRAMES):
            if self._stop.is_set():
                return
            try:
                msg = self.messages.get(timeout=0.1)
            except Empty:
                self._tick(frame)
                continue
            self._handle(msg)

    def stop(self):
        self._stop.set()

    def _tick(self, frame):
        """刷一帧 spinner（仅流式期间）。"""
        if not self._streaming:
            return
        elapsed = int(time.monotonic() - self._start)
        sys.stdout.write(
            f"\r\x1b[2m{frame} {self._label} · {self._tokens} tokens · {elapsed}s\x1b[0m\x1b[K"
        )
        sys.stdout.flush()

    def _clear_line(self):
        if self._streaming:
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
            self._streaming = False

    # ── JSON-RPC 分发（渲染） ─────────────────────────────
    def _handle(self, msg: dict):
        """按 method 分发单条 JSON-RPC dict。未知 method 忽略。"""
        method = msg.get("method")
        params = msg.get("params", {})
        if method == "window/thinking":
            self._on_thinking()
        elif method == "window/delta":
            self._on_delta(params.get("token", ""))
        elif method == "window/flush":
            self._on_flush(params.get("text", ""))
        elif method == "window/display":
            self._on_display(params.get("content", ""))
        # window/user 及未知 method：终端不处理

    def _start_stream(self):
        if self._start is None:
            self._start = time.monotonic()
        self._streaming = True

    def _on_thinking(self):
        self._tokens += 1
        self._start_stream()

    def _on_delta(self, token):
        if self._label != "回复中":     # 首个 content token：切阶段
            self._label = "回复中"
            self._tokens = 0
            self._start = time.monotonic()
        self._buf += token
        self._tokens += 1
        self._start_stream()

    def _on_flush(self, text=""):
        """清 spinner 行、Rich 渲染正文、复位。text 全文兜底优先于本地 buf。幂等。"""
        self._clear_line()
        body = text or self._buf         # 协议全文兜底优先
        if body:
            folded = _fold_exec_blocks(body)
            clean = folded.replace("<EXEC>", "").replace("</EXEC>", "")
            console.print(Markdown(clean))
        self._buf = ""
        self._tokens = 0
        self._label = "思考中"
        self._start = None

    def _on_display(self, content):
        """显示命令结果等非流式消息。"""
        self._clear_line()
        if content:
            console.print(content)
