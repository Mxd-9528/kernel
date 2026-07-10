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
        """收到流式 token，逐字符 Live 渲染。"""
        if self._live is None:
            self._live = Live(
                Markdown(""),
                refresh_per_second=60,
                screen=False,
                vertical_overflow="visible",
            )
            self._live.start()
            self._collected = ""
        for ch in token:
            self._collected += ch
            self._live.update(Markdown(self._collected))
            time.sleep(0.008)

    def on_display(self, content):
        """收到完整消息：先 flush 流式渲染，再打印内容。"""
        self._flush()
        if content:
            print(content)

    def _flush(self):
        """停止流式 Live 渲染，清空缓冲区。"""
        if self._live is not None:
            self._live.stop()
            self._live = None
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
