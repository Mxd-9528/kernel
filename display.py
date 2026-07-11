import time

from rich.live import Live
from rich.markdown import Markdown

from agent import on


# ── 事件驱动渲染：订阅 display_delta / display ──────────────────────

class _TerminalDisplay:
    """终端渲染实例。封装 Rich Live 状态，供 display_delta / display 事件驱动。"""

    def __init__(self):
        self._live = None
        self._collected = ""

    def on_delta(self, token):
        """收到流式 token，累加后逐字符渲染。"""
        self._collected += token.replace("<EXEC>", "").replace("</EXEC>", "")
        self._start()
        for ch in token:
            self._render(self._collected)
            time.sleep(0.008)

    def _start(self):
        """启动渲染后端。"""
        if self._live is not None:
            return
        self._live = Live(
            Markdown(""),
            refresh_per_second=60,
            screen=False,
            vertical_overflow="visible",
        )
        self._live.start()

    def _render(self, text):
        """渲染文本到终端。"""
        self._live.update(Markdown(text))

    def _stop(self):
        """停止渲染后端。"""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def on_display(self, content):
        """收到完整消息：先 flush 流式渲染，再打印内容。"""
        self._flush()
        if content:
            print(content)

    def _flush(self):
        """停止渲染，清空缓冲区。"""
        self._stop()
        self._collected = ""


_display = _TerminalDisplay()


@on("display_delta")
def _on_display_delta(token):
    _display.on_delta(token)


@on("display")
def _on_display(content):
    _display.on_display(content)


@on("display_flush")
def _on_display_flush():
    _display._flush()
