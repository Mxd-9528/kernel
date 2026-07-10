import time

from rich.live import Live
from rich.markdown import Markdown

from agent import on


# ── 事件驱动渲染：订阅 display_delta / display ──────────────────────

_live = None
_collected = ""


@on("display_delta")
def _on_display_delta(token):
    """收到流式 token，逐字符 Live 渲染。"""
    global _live, _collected
    if _live is None:
        _live = Live(
            Markdown(""),
            refresh_per_second=60,
            screen=False,
            vertical_overflow="visible",
        )
        _live.start()
        _collected = ""
    for ch in token:
        _collected += ch
        _live.update(Markdown(_collected))
        time.sleep(0.008)


@on("display")
def _on_display(content):
    """收到完整消息：停止流式 Live，打印内容。"""
    global _live
    if _live is not None:
        _live.stop()
        _live = None
    if content:
        print(content)
