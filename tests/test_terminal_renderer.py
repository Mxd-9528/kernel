"""TerminalRenderer 测试：从 JSON-RPC 队列消费 dict → rich 渲染。

终端是协议的第二个消费者（与 WebSocket server 对称）。
验证协议可承载不同显示层：同一套 5 种 JSON-RPC dict，Web 与终端各自消费。

TDD 红灯：TerminalRenderer 尚未实现，此测试应失败。
"""

import threading
import time
from queue import Queue
from rich.markdown import Markdown


def _msg(method, **params):
    return {"jsonrpc": "2.0", "method": method, "params": params}


def test_renderer_takes_queue():
    """TerminalRenderer 构造接受一个 messages 队列。"""
    from kernel.display import TerminalRenderer
    q = Queue()
    r = TerminalRenderer(q)
    assert r.messages is q


def test_handle_thinking_then_delta_switches_label():
    """thinking → delta：label 从思考中切到回复中，tokens 归零重算。"""
    from kernel.display import TerminalRenderer
    r = TerminalRenderer(Queue())
    r._handle(_msg("window/thinking", token="t1"))
    r._handle(_msg("window/thinking", token="t2"))
    assert r._label == "思考中"
    assert r._tokens == 2
    r._handle(_msg("window/delta", token="hello "))
    assert r._label == "回复中"
    assert r._tokens == 1
    r._handle(_msg("window/delta", token="world"))
    assert r._buf == "hello world"
    assert r._tokens == 2


def test_flush_renders_markdown_and_resets():
    """flush 渲染累积正文为 Markdown，清洗 EXEC，之后状态复位；空 flush 幂等不渲染。"""
    from kernel import display
    r = display.TerminalRenderer(Queue())
    rendered = []
    orig = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        r._handle(_msg("window/delta", token="hello <EX"))
        r._handle(_msg("window/delta", token="EC>code</EXEC> world"))
        r._handle(_msg("window/flush", text=""))
        assert len(rendered) == 1
        assert isinstance(rendered[0], Markdown)
        assert "<EXEC>" not in rendered[0].markup
        assert "code" in rendered[0].markup
        # 复位
        assert r._buf == ""
        assert r._label == "思考中"
        # 空 flush 幂等：不再渲染
        r._handle(_msg("window/flush", text=""))
        assert len(rendered) == 1
    finally:
        display.console.print = orig


def test_flush_prefers_protocol_text():
    """flush 的 params.text 全文兜底优先于本地累积 buf——验证协议 text 承载全文。"""
    from kernel import display
    r = display.TerminalRenderer(Queue())
    rendered = []
    orig = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        # 本地 buf 只累积了片段
        r._handle(_msg("window/delta", token="partial"))
        # 但协议 flush 传来全文——应以全文为准
        r._handle(_msg("window/flush", text="full text from protocol"))
        assert len(rendered) == 1
        assert "full text from protocol" in rendered[0].markup
        assert "partial" not in rendered[0].markup
    finally:
        display.console.print = orig


def test_handle_display_prints_content():
    """window/display → console.print 一次性消息。"""
    from kernel import display
    r = display.TerminalRenderer(Queue())
    rendered = []
    orig = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        r._handle(_msg("window/display", content="系统消息"))
        assert rendered == ["系统消息"]
    finally:
        display.console.print = orig


def test_handle_ignores_user_and_unknown():
    """window/user 及未知 method 不崩溃（终端不回显用户输入）。"""
    from kernel.display import TerminalRenderer
    r = TerminalRenderer(Queue())
    r._handle(_msg("window/user", content="x"))     # 不崩
    r._handle(_msg("window/unknown", foo="bar"))    # 不崩


def test_run_loop_consumes_and_stops():
    """run() 后台线程消费队列，stop() 后退出。集成验证队列消费路径。"""
    from kernel import display
    q = Queue()
    r = display.TerminalRenderer(q)
    rendered = []
    orig = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        t = threading.Thread(target=r.run, daemon=True)
        t.start()
        q.put(_msg("window/delta", token="hi"))
        q.put(_msg("window/flush", text="hi"))
        # 等消费
        for _ in range(50):
            if rendered:
                break
            time.sleep(0.02)
        r.stop()
        t.join(timeout=1)
        assert not t.is_alive()
        assert len(rendered) == 1
        assert "hi" in rendered[0].markup
    finally:
        display.console.print = orig
