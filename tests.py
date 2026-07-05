"""核心 harness 测试：result/run/extract/agent/manifest/inject。运行本文件跑全部（含工具）。"""


def test_result():
    from result import Result, ListResult, DictResult
    r = Result("hi", error=None, stdout="hi")
    assert str(r) == "hi" and r.error is None and r.stdout == "hi" and r.facts == {"stdout": "hi"}

    lr = ListResult([1, 2], error=None, rowcount=2)
    assert list(lr) == [1, 2] and lr.rowcount == 2 and lr.error is None

    dr = DictResult({"a": 1}, error=None)
    assert dr["a"] == 1 and dr.error is None

    err = ValueError("boom")
    e = Result("", error=err)
    assert e.error is err

    try:
        Result("x")
    except TypeError:
        pass
    else:
        raise AssertionError("漏传 error= 应该报 TypeError")

    # __repr__ 是三元组到达模型的坍缩点：Body + error + facts 一次性倒出。
    assert "正文" in repr(Result("正文", error=None, lines=2))
    assert "FileNotFoundError" in repr(Result("", error=FileNotFoundError("no")))
    print("result ok")


def test_run():
    from run import run
    r = run("1 + 1")
    assert r == "2" and r.error is None and r.facts == {}  # 成功无附加事实，facts 干净不重复
    r = run("print('hi')")
    assert r == "hi" and r.error is None
    r = run("x = 5")
    assert r == "" and r.error is None
    assert run("x") == "5"
    r = run("1/0")
    assert r == "" and isinstance(r.error, ZeroDivisionError)
    r = run("print('a'); 1/0")
    assert r.stdout.startswith("a") and isinstance(r.error, ZeroDivisionError)
    assert "\x1b[" not in r.stdout
    print("run ok")


def test_extract():
    from extract import extract
    reply = '<!EXEC>\n```python\ns = "他说```你好```"\nprint(s)\nfor i in range(2):\n    print(i)\n```\n</EXEC>'
    blocks = extract(reply)
    assert len(blocks) == 1
    code = blocks[0]
    assert code.startswith('s = "他说')
    assert "for i in range(2):" in code
    assert code.endswith("print(i)")
    assert code.count("\n") == 3

    multi = '<!EXEC>\n```python\n1 + 1\n```\n</EXEC>\n中间文字\n<!EXEC>\n```python\nprint("hello")\n```\n</EXEC>'
    blocks = extract(multi)
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
    original = agent_mod.call
    agent_mod.call = lambda *a, **kw: next(fake_replies)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result, _ = agent("测试：算 1+1，再算 3*4")
        assert result == "做完了，结果是 12。", repr(result)
        print("agent ok")
    finally:
        agent_mod.call = original


def test_manifest():
    from manifest import presets, list_tools
    # 扫 tools/：每个 tools/x.py 的同名函数 x 就是预置函数
    names = {name for name, _ in presets()}
    assert "read" in names  # read.py 在 tools/ 里，必被扫到
    # 描述含函数名、签名、docstring 首行；不手写 schema，全自省
    text = list_tools()
    assert "read(file_path, offset=None, limit=None)" in text
    assert "读文件" in text  # docstring 来自 read.__doc__
    print("manifest ok")


def test_inject():
    # 回归：启动路径（run）必须自动把预置函数注入 user_ns
    from run import run
    for f in ("read", "write", "edit", "glob", "grep", "bash"):
        assert f in run("dir()"), f"{f} 未注入命名空间"
    # 机件与 inspect 也在
    assert "inspect" in run("dir()") and "Result" in run("dir()")
    # 回归：模型在内核里重绑预置函数，后续轮次不被 inject 覆盖（持久内核核心优势）
    run("glob = lambda *a: '热补丁版'")
    run("1+1")  # 再跑一轮，会再调 inject——不能覆盖上面的重绑
    assert run("glob('x')") == "'热补丁版'", "重绑被 inject 覆盖了——持久性被破坏"
    run("from tools.glob import glob")  # 还原成真 glob，避免污染后续测试
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
    from agent import feedback
    from result import Result
    # 单块：[环境反馈] 开头，无代码块编号，repr 原样转达三元组
    one = feedback([Result("正文", error=None, lines=2)])
    assert one.startswith("[环境反馈]")
    assert "正文" in one and "lines=2" in one
    assert "代码块" not in one  # 单块不加编号

    # 多块：每块加 --- 代码块 N --- 分隔
    multi = feedback([Result("a", error=None), Result("b", error=None)])
    assert "--- 代码块 1 ---" in multi and "--- 代码块 2 ---" in multi
    assert "a" in multi and "b" in multi

    # 空 body 且无 facts → (无输出)
    empty = feedback([Result("", error=None)])
    assert "(无输出)" in empty
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
    from skills import skills, list_skills
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
    from _compact import split_history, compact

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
    import _compact as compact_mod
    compact_mod.call = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("不该调用"))
    assert compact(big, keep=6, threshold=1_000_000) == big

    # 过阈值：mock 压缩 API，验证重组结构
    compact_mod.call = lambda msgs, model: "【摘要】"
    new = compact(conv(10), keep=6, threshold=1)
    assert new[0] == {"role": "system", "content": "sys"}  # system 保留
    assert any(m["role"] == "assistant" and "【摘要】" in m["content"] for m in new)
    assert new[-1] == {"role": "assistant", "content": "a9"}  # 最近6轮原样在末尾
    assert len(new) < len(conv(10))
    print("compact ok")


if __name__ == "__main__":
    test_result()
    test_run()
    test_extract()
    test_agent()
    test_manifest()
    test_inject()
    test_inject_sentinel()
    test_feedback()
    test_history()
    test_skills()
    test_compact()
    # 接口 = 实现的 re-export：签名一致 = 同一对象。
    import call, _call, background, _background, compact, _compact, run, _run
    assert call.call is _call.call, "call 接口漂移"
    assert call.default_model is _call.default_model, "call.default_model 接口漂移"
    for fn in ("run_with_timeout", "task_status", "task_cancel"):
        assert getattr(background, fn) is getattr(_background, fn), f"background.{fn} 接口漂移"
    assert compact.compact is _compact.compact, "compact 接口漂移"
    assert run.run is _run.run, "run 接口漂移"
    # 视野即依赖：上游源码不应出现 _* 实现模块名（认知链不穿透接口）。
    from pathlib import Path
    exempt = {"_call.py", "call.py", "_background.py", "background.py",
              "_compact.py", "compact.py", "_run.py", "run.py",
              "tests.py"}  # 实现自身、接口（转手）、测试跨水线特权
    for src in Path(".").glob("*.py"):
        if src.name in exempt:
            continue
        text = src.read_text("utf-8")
        for name in ("_call", "_background", "_compact", "_run"):
            assert "from {} import".format(name) not in text, f"{src.name} 认知链穿透 {name}"
            # 裸 import：拦 "import _xxx" 后接空白/逗号/行尾（"import _call_stub" 不误伤——不同名）
            import re
            assert not re.search(r"(?m)^\s*import\s+{}(?:\s|,|$)".format(re.escape(name)), text), f"{src.name} 认知链穿透 {name}"
    print("contract ok")
    import tests_tools
    tests_tools.run_all()
    print("全部通过")
