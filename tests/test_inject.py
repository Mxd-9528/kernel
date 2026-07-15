"""inject 模块测试。"""


def test_inject():
    """回归：模型在内核里重绑预置函数，后续轮次不被 inject 覆盖。"""
    from kernel.runtime import _run_cell
    _run_cell("glob = lambda *a: '热补丁版'")
    _run_cell("1+1")
    assert _run_cell("glob('x')") == "热补丁版", "重绑被 inject 覆盖了"
    _run_cell("from kernel.tools.glob import glob")
    print("inject ok")


def test_inject_sentinel():
    """哨兵机制：首次注入后二次调用被拦截。"""
    from kernel.inject import inject

    class FakeShell:
        def __init__(self):
            self.user_ns = {}
            self.pushed = 0
        def push(self, ns):
            self.pushed += 1
            self.user_ns.update(ns)

    sh = FakeShell()
    inject(sh)
    assert sh.pushed == 1, "首次应注入"
    assert getattr(sh, "_kernel_injected", False) is True

    sh.user_ns.clear()
    inject(sh)
    assert sh.pushed == 1, "哨兵失效：user_ns 空也重注入了"

    sh2 = FakeShell()
    inject(sh2)
    assert sh2.pushed == 1
    print("inject sentinel ok")
