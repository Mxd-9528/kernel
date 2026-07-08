"""核心 harness 测试：extract/agent/manifest/inject/feedback。运行本文件跑全部（含工具）。"""


def test_run_cell():
    """_run_cell 返回原生 Python 值；异常直接 raise（含 traceback）。"""
    from runtime import _run_cell

    # 表达式值
    assert _run_cell("1 + 1") == 2
    # 无值（stdout 兜底）
    assert _run_cell("print('hi')") == "hi"
    # 语句无输出
    assert _run_cell("x = 5") is None
    # 上一步的 x 在内核里
    assert _run_cell("x") == 5
    # 异常 raise
    try:
        _run_cell("1/0")
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError("应 raise ZeroDivisionError")
    # 异常前的 stdout 会附到异常上
    try:
        _run_cell("print('a'); 1/0")
    except ZeroDivisionError as e:
        assert getattr(e, "_kernel_stdout", "").startswith("a")
    # 语法错误：IPython 放在 error_before_exec，不是 error_in_exec——回归防护
    try:
        _run_cell("def bad(:")
    except SyntaxError:
        pass
    else:
        raise AssertionError("语法错误应 raise SyntaxError")
    print("run_cell ok")


def test_extract():
    import re
    _p = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"
    def _x(t): return [m.strip() for m in re.findall(_p, t, re.DOTALL)]
    reply = '<!EXEC>\n```python\ns = "他说```你好```"\nprint(s)\nfor i in range(2):\n    print(i)\n```\n</EXEC>'
    blocks = _x(reply)
    assert len(blocks) == 1
    code = blocks[0]
    assert code.startswith('s = "他说')
    assert "for i in range(2):" in code
    assert code.endswith("print(i)")
    assert code.count("\n") == 3

    multi = '<!EXEC>\n```python\n1 + 1\n```\n</EXEC>\n中间文字\n<!EXEC>\n```python\nprint("hello")\n```\n</EXEC>'
    blocks = _x(multi)
    assert len(blocks) == 2
    assert blocks[0] == "1 + 1"
    assert blocks[1] == 'print("hello")'
    print("extract ok")


def test_agent():
    import contextlib, io
    from agent import agent
    fake_replies = iter([
        '来做：\n<!EXEC>\n```python\n1 + 1\n```\n</EXEC>',
        '答案是 2，再算一个：\n<!EXEC>\n```python\nx = 3 * 4\nprint(x)\n```\n</EXEC>',
        '做完了，结果是 12。',
    ])
    import agent as agent_mod
    original = agent_mod.stream_chat
    def _mock_stream(*a, **kw):
        yield next(fake_replies)
    agent_mod.stream_chat = _mock_stream
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result, _ = agent("测试：算 1+1，再算 3*4")
        assert result == "做完了，结果是 12。", repr(result)
        print("agent ok")
    finally:
        agent_mod._stream_chat = original


def test_manifest():
    from system import presets, list_tools
    # 扫 tools/：每个 tools/x.py 的同名函数 x 就是预置函数
    names = {name for name, _ in presets()}
    assert "read" in names  # read.py 在 tools/ 里，必被扫到
    # 描述含函数名、签名、docstring 首行；不手写 schema，全自省
    text = list_tools()
    assert "read(file_path, offset=None, limit=None)" in text
    assert "读文件" in text  # docstring 来自 read.__doc__
    print("manifest ok")


def test_inject():
    # 回归：模型在内核里重绑预置函数，后续轮次不被 inject 覆盖（持久内核核心优势）
    from runtime import _run_cell
    _run_cell("glob = lambda *a: '热补丁版'")
    _run_cell("1+1")  # 再跑一轮，会再调 inject——不能覆盖上面的重绑
    assert _run_cell("glob('x')") == "热补丁版", "重绑被 inject 覆盖了——持久性被破坏"
    _run_cell("from tools.glob import glob")  # 还原成真 glob，避免污染后续测试
    print("inject ok")


def test_inject_sentinel():
    # 哨兵机制专项：不依赖任何工具名，纯粹验证"已注入"的标记
    from inject import inject
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
    assert getattr(sh, "_kernel_injected", False) is True, "哨兵未打标记"

    # 二次调用应被拦截——即使 user_ns 里没有任何工具名
    sh.user_ns.clear()  # 模拟工具改名/删除的极端情况
    inject(sh)
    assert sh.pushed == 1, "哨兵失效：user_ns 空也重注入了"

    # 全新 shell 无哨兵，才会注入
    sh2 = FakeShell()
    inject(sh2)
    assert sh2.pushed == 1
    print("inject sentinel ok")


def test_feedback():
    from runtime import feedback
    # 单块：[环境反馈] 开头，无代码块编号
    one = feedback(["hello"])
    assert one.startswith("[环境反馈]")
    assert "hello" in one
    assert "代码块" not in one  # 单块不加编号

    # 多块：每块加 --- 代码块 N --- 分隔
    multi = feedback(["a", "b"])
    assert "--- 代码块 1 ---" in multi and "--- 代码块 2 ---" in multi
    assert "a" in multi and "b" in multi

    # None → (无输出)
    empty = feedback([None])
    assert "(无输出)" in empty

    # 异常 → traceback
    try:
        1 / 0
    except ZeroDivisionError as e:
        exc = e
    err_out = feedback([exc])
    assert "ZeroDivisionError" in err_out

    # 原生类型 → repr
    lst_out = feedback([[1, 2, 3]])
    assert "[1, 2, 3]" in lst_out

    # 大输出自动截断（40/20/40 头/中/尾）：防止 read 大日志/bash cat 大文件爆上下文
    # 头 8000 + 中 4000 + 尾 8000 = 20000 有效字符 + 标签开销 (<1000)
    huge = "x" * 30000
    trunc_out = feedback([huge])
    assert 15000 < len(trunc_out) < 22000, f"截断异常：{len(trunc_out)} 字符"
    assert "截断" in trunc_out and "40%/20%/40%" in trunc_out
    print("feedback ok")


def test_history():
    import tempfile
    import os
    from history import save, load
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "h.json")

        # 没有文件时 load 返回 None（启动无历史）
        assert load(p) is None

        # 存取往返
        msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
        save(msgs, p)
        assert load(p) == msgs

        # 损坏文件：当无历史处理，不崩
        with open(p, "w", encoding="utf-8") as f:
            f.write("{坏 json")
        assert load(p) is None
    print("history ok")


def test_skills():
    import tempfile
    import os
    from system import skills, list_skills
    with tempfile.TemporaryDirectory() as d:
        # 造两个 skill：标准 frontmatter
        os.makedirs(os.path.join(d, "foo"))
        with open(os.path.join(d, "foo", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: foo\ndescription: 做 foo 的事\n---\n\n# 正文很长...\n")
        os.makedirs(os.path.join(d, "bar"))
        with open(os.path.join(d, "bar", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: bar\ndescription: 做 bar 的事\n---\n")
        # 没有 SKILL.md 的目录：忽略，不崩
        os.makedirs(os.path.join(d, "empty"))

        got = dict(skills(d))
        assert got["foo"] == "做 foo 的事" and got["bar"] == "做 bar 的事"

        # list_skills：含名字、描述、和「按需 read」的引导
        text = list_skills(d)
        assert "foo" in text and "做 foo 的事" in text
        assert "SKILL.md" in text  # 告诉模型去哪 read

        # 没有 skills 目录：返回空，不崩
        assert skills(os.path.join(d, "nonexistent")) == []
    print("skills ok")


def test_compact():
    from compact import split_history, compact

    def conv(n):
        # 造 n 轮对话：每轮 user + assistant
        h = [{"role": "system", "content": "sys"}]
        for i in range(n):
            h.append({"role": "user", "content": f"u{i}"})
            h.append({"role": "assistant", "content": f"a{i}"})
        return h

    # split：system 单独、保留最近 keep 轮（数 assistant）、其余可压
    h = conv(10)
    system, mid, recent = split_history(h, keep=6)
    assert system == [{"role": "system", "content": "sys"}]
    assert sum(1 for m in recent if m["role"] == "assistant") == 6  # 最近6轮
    assert sum(1 for m in mid if m["role"] == "assistant") == 4  # 前4轮可压
    assert system + mid + recent == h  # 无遗漏无重叠

    # 未过阈值：原样返回（不调用 LLM）
    big = conv(10)
    import compact as compact_mod
    compact_mod.stream_chat = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("不该调用"))
    assert compact(big, keep=6, threshold=1_000_000) == big

    # 过阈值：mock 压缩 API，验证重组结构
    compact_mod.stream_chat = lambda *a, **kw: iter(["【摘要】"])
    new = compact(conv(10), keep=6, threshold=1)
    assert new[0] == {"role": "system", "content": "sys"}  # system 保留
    assert any(m["role"] == "assistant" and "【摘要】" in m["content"] for m in new)
    assert new[-1] == {"role": "assistant", "content": "a9"}  # 最近6轮原样在末尾
    assert len(new) < len(conv(10))
    print("compact ok")


if __name__ == "__main__":
    # 自动扫本模块 test_* 函数按定义顺序执行；加测试只加 def test_xxx，不用改此段。
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    import tests_tools
    tests_tools.run_all()
    print("全部通过")
