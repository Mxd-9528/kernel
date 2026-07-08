import time

from rich.live import Live
from rich.markdown import Markdown


def render_stream(tokens_iter):
    """逐 token 用 Rich Live 增量渲染 Markdown，返回完整文本。"""
    collected = ""
    live = Live(
        Markdown(""),
        refresh_per_second=60,
        screen=False,
        vertical_overflow="visible",
    )
    live.start()
    try:
        for token in tokens_iter:
            collected += token
            live.update(Markdown(collected))
            time.sleep(0.008)
    finally:
        live.stop()
    return collected
