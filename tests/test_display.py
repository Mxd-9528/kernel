"""display 模块测试。"""

import threading
from rich.markdown import Markdown


def test_spinner_state_machine():
    """_Spinner 状态机：累加、清洗 EXEC、flush 渲染、幂等、空 flush 不渲染。"""
    from kernel import display
    s = display._Spinner()
    rendered = []
    orig_print = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()
        s._thread = t

        s.on_thinking("t1")
        s.on_thinking("t2")
        assert s._label == "思考中" and s._tokens == 2
        s.on_delta("hello <EX")
        assert s._label == "回复中" and s._tokens == 1
        s.on_delta("EC>code</EXEC> world")
        assert s._buf == "hello <EXEC>code</EXEC> world"
        assert s._tokens == 2

        s.on_flush()
        assert len(rendered) == 1
        assert isinstance(rendered[0], Markdown)
        assert "<EXEC>" not in rendered[0].markup and "code" in rendered[0].markup

        s.on_flush()
        assert len(rendered) == 1

        rendered.clear()
        s.on_flush()
        assert rendered == []
    finally:
        display.console.print = orig_print
    print("spinner_state_machine ok")


def test_spinner_observer():
    """spinner 是 BaseObserver 实例。"""
    from kernel.observer import BaseObserver
    from kernel.display import spinner
    assert isinstance(spinner, BaseObserver)
    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    methods = {m for m in dir(spinner) if not m.startswith("_") and callable(getattr(spinner, m))}
    missing = required - methods
    assert not missing, f"spinner 缺少方法: {missing}"
    print("spinner_observer ok")


def test_fold_exec_blocks():
    from kernel.display import _fold_exec_blocks
    text = "<EXEC>\n```python\nprint('hello')\n```\n</EXEC>"
    result = _fold_exec_blocks(text)
    assert "<EXEC>" not in result
    assert "hello" in result or "print" in result
    print("fold_exec_blocks ok")
