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

    # __repr__ 是三元组到达模型的坍缩点：Body + error（非None才显示）+ facts 整字典倒出，不挑字段。
    # 工具成功：facts 字段（无 stdout）原样转达
    rep = repr(Result("正文", error=None, file_path="x.py", lines=2))
    assert "正文" in rep and "file_path='x.py'" in rep and "lines=2" in rep and "error=" not in rep
    # 工具失败：facts 没有 stdout 字段也不崩（根除写死字段的 bug），error 显示
    rep = repr(Result("", error=FileNotFoundError("no"), file_path="x.py"))
    assert "error=" in rep and "FileNotFoundError" in rep and "file_path='x.py'" in rep
    # 业务失败（returncode非0）进 facts，工具自身 error=None：不显示 error
    rep = repr(Result("out", error=None, returncode=127))
    assert "returncode=127" in rep and "error=" not in rep
    # list/dict Body 形态
    assert "rowcount=2" in repr(ListResult([1, 2], error=None, rowcount=2))
    assert "kind='INSERT'" in repr(DictResult({"n": 1}, error=None, kind="INSERT"))
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
    from agent import agent
    fake_replies = iter([
        '来做：\n<!EXEC>\n```python\n1 + 1\n```\n</EXEC>',
        '答案是 2，再算一个：\n<!EXEC>\n```python\nx = 3 * 4\nprint(x)\n```\n</EXEC>',
        '做完了，结果是 12。',
    ])
    import call as call_mod
    original = call_mod.call
    call_mod.call = lambda *a, **kw: next(fake_replies)
    try:
        result, _ = agent("测试：算 1+1，再算 3*4")
        assert result == "做完了，结果是 12。", repr(result)
        print("agent ok")
    finally:
        call_mod.call = original


def test_manifest():
    from manifest import presets, describe
    # 扫 tools/：每个 tools/x.py 的同名函数 x 就是预置函数
    names = {name for name, _ in presets()}
    assert "read" in names  # read.py 在 tools/ 里，必被扫到
    # 描述含函数名、签名、docstring 首行；不手写 schema，全自省
    text = describe()
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


def test_build_system():
    from agent import build_system
    sys = build_system()
    # 含 prompt.txt 内容 + 预置函数清单（manifest 自动拼）
    assert "预置函数" in sys
    assert "read(file_path" in sys  # describe() 的产物
    print("build_system ok")


def test_history():
    import tempfile
    import os
    from history import save, load
    d = tempfile.mkdtemp()
    p = os.path.join(d, "h.json")

    # 没有文件时 load 返回 None（启动无历史）
    assert load(p) is None

    # 存取往返
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    save(msgs, p)
    assert load(p) == msgs

    # 存盘清掉 reasoning_content（隐私+体积），但不改传入的原列表
    withr = [{"role": "assistant", "content": "答案", "reasoning_content": "思考过程"}]
    save(withr, p)
    loaded = load(p)
    assert "reasoning_content" not in loaded[0]
    assert loaded[0]["content"] == "答案"
    assert "reasoning_content" in withr[0]  # 原列表不被改

    # 损坏文件：当无历史处理，不崩
    with open(p, "w", encoding="utf-8") as f:
        f.write("{坏 json")
    assert load(p) is None

    import shutil
    shutil.rmtree(d)
    print("history ok")


def test_skills():
    import tempfile
    import os
    import shutil
    from skills import skills, describe_skills
    d = tempfile.mkdtemp()
    # 造两个 skill：标准 frontmatter
    os.makedirs(os.path.join(d, "foo"))
    with open(os.path.join(d, "foo", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: foo\ndescription: 做 foo 的事\n---\n\n# 正文很长...\n")
    os.makedirs(os.path.join(d, "bar"))
    with open(os.path.join(d, "bar", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: bar\ndescription: 做 bar 的事\n---\n")
    # 没有 SKILL.md 的目录：忽略，不崩
    os.makedirs(os.path.join(d, "empty"))
    # 多行 description（YAML 折叠语法）：手写 split 会读错，yaml 能正确合并
    os.makedirs(os.path.join(d, "baz"))
    with open(os.path.join(d, "baz", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: baz\ndescription: >\n  第一行\n  第二行\n---\n")

    got = dict(skills(d))
    assert got["foo"] == "做 foo 的事" and got["bar"] == "做 bar 的事"
    assert "第一行" in got["baz"] and "第二行" in got["baz"], got["baz"]  # 多行被正确合并

    # describe_skills：含名字、描述、和「按需 read」的引导
    text = describe_skills(d)
    assert "foo" in text and "做 foo 的事" in text
    assert "SKILL.md" in text  # 告诉模型去哪 read

    # 没有 skills 目录：返回空，不崩
    assert skills(os.path.join(d, "nonexistent")) == []
    assert describe_skills(os.path.join(d, "nonexistent")) == ""

    shutil.rmtree(d)
    print("skills ok")


def test_compact():
    from compact import split_history, should_compact, compact

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

    # 对话太短（不足 keep 轮）：中间为空，全保留
    short = conv(3)
    system, mid, recent = split_history(short, keep=6)
    assert mid == [] and system + recent == short

    # should_compact：中间部分超阈值才触发
    assert should_compact(conv(3), keep=6, threshold=10) is False  # 太短，中间空
    big = conv(10)
    assert should_compact(big, keep=6, threshold=1_000_000) is False  # 没超阈值
    assert should_compact(big, keep=6, threshold=1) is True  # 超阈值

    # compact：mock 压缩 API，验证重组结构
    h = conv(10)
    new = compact(h, keep=6, call_compress=lambda msgs: "【摘要】")
    assert new[0] == {"role": "system", "content": "sys"}  # system 保留
    # 摘要作为 user/assistant 对插入
    assert any(m["role"] == "assistant" and "【摘要】" in m["content"] for m in new)
    # 最近6轮原样在末尾
    assert new[-1] == {"role": "assistant", "content": "a9"}
    assert len(new) < len(h)  # 确实压短了

    # compress：拼压缩请求（这次提出来才能测——COMPRESS_PROMPT 拼装 + 序列化）
    import json
    from compact import compress, COMPRESS_PROMPT
    captured = {}
    def fake_call(msgs, model):
        captured["msgs"], captured["model"] = msgs, model
        return "压缩结果"
    mid = [{"role": "user", "content": "u0"}, {"role": "assistant", "content": "a0"}]
    out = compress(mid, "ark-code", fake_call)
    assert out == "压缩结果"
    assert captured["model"] == "ark-code"  # 用传入的 model
    assert captured["msgs"][0] == {"role": "system", "content": COMPRESS_PROMPT}  # system=压缩prompt
    assert json.loads(captured["msgs"][1]["content"]) == mid  # user=待压内容的json
    print("compact ok")


if __name__ == "__main__":
    test_result()
    test_run()
    test_extract()
    test_agent()
    test_manifest()
    test_inject()
    test_feedback()
    test_build_system()
    test_history()
    test_skills()
    test_compact()
    import tests_tools
    tests_tools.run_all()
    print("全部通过")
