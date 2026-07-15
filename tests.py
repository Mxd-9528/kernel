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
    _p = r"<EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"
    def _x(t): return [m.strip() for m in re.findall(_p, t, re.DOTALL)]
    reply = '<EXEC>\n```python\ns = "他说```你好```"\nprint(s)\nfor i in range(2):\n    print(i)\n```\n</EXEC>'
    blocks = _x(reply)
    assert len(blocks) == 1
    code = blocks[0]
    assert code.startswith('s = "他说')
    assert "for i in range(2):" in code
    assert code.endswith("print(i)")
    assert code.count("\n") == 3

    multi = '<EXEC>\n```python\n1 + 1\n```\n</EXEC>\n中间文字\n<EXEC>\n```python\nprint("hello")\n```\n</EXEC>'
    blocks = _x(multi)
    assert len(blocks) == 2
    assert blocks[0] == "1 + 1"
    assert blocks[1] == 'print("hello")'
    print("extract ok")


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


def test_display():
    """_Spinner 状态机：累加、清洗 EXEC、flush 渲染、幂等、空 flush 不渲染。
    后台 spinner 线程被跳过——测试只关心状态与渲染合同。"""
    import display
    import threading
    from rich.markdown import Markdown
    s = display._Spinner()
    rendered = []
    orig_print = display.console.print
    display.console.print = lambda *a, **kw: rendered.append(a[0])
    try:
        # 占位线程（已结束，可 join）；on_delta 中 _thread is None 判断跳过起新线程
        t = threading.Thread(target=lambda: None)
        t.start(); t.join()
        s._thread = t

        # thinking → content 阶段切换：thinking 计数、content 首个 token 归零重计
        s.on_thinking("t1")
        s.on_thinking("t2")
        assert s._label == "思考中" and s._tokens == 2
        s.on_delta("hello <EX")
        assert s._label == "回复中" and s._tokens == 1  # 切阶段清零，加当前 token
        s.on_delta("EC>code</EXEC> world")
        assert s._buf == "hello <EXEC>code</EXEC> world", f"累加异常: {s._buf}"
        assert s._tokens == 2

        # on_flush 触发一次渲染：Markdown 对象、内容已清洗
        s.on_flush()
        assert len(rendered) == 1, f"应渲染一次: {len(rendered)}"
        assert isinstance(rendered[0], Markdown)
        assert "<EXEC>" not in rendered[0].markup and "code" in rendered[0].markup

        # 幂等：再 on_flush 不再渲染
        s.on_flush()
        assert len(rendered) == 1, "on_flush 非幂等"

        # 空 buf on_flush 不触发渲染
        rendered.clear()
        s.on_flush()
        assert rendered == []
    finally:
        display.console.print = orig_print
    print("display ok")


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
    compact_mod.stream_chat = lambda *a, **kw: iter([("content", "【摘要】")])
    new = compact(conv(10), keep=6, threshold=1)
    assert new[0] == {"role": "system", "content": "sys"}  # system 保留
    assert any(m["role"] == "assistant" and "【摘要】" in m["content"] for m in new)
    assert new[-1] == {"role": "assistant", "content": "a9"}  # 最近6轮原样在末尾
    assert len(new) < len(conv(10))

    # 去重：重复的 [环境反馈] 内容旧的替换为引用行，最新保留
    from compact import _dedup_tool_outputs
    mid = [
        {"role": "user", "content": "[环境反馈] hello"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "[环境反馈] hello"},   # 重复
        {"role": "assistant", "content": "ok2"},
        {"role": "user", "content": "[环境反馈] different"},
        {"role": "assistant", "content": "ok3"},
        {"role": "user", "content": "[环境反馈] hello"},   # 又重复
    ]
    out = _dedup_tool_outputs(list(mid))
    assert out[0]["content"].startswith("[环境反馈同下文"), f"第 0 条应替换为引用: {out[0]}"
    assert out[2]["content"].startswith("[环境反馈同下文"), f"第 2 条应替换为引用: {out[2]}"
    assert out[4] == mid[4], "不同内容不应受影响"
    assert out[6] == mid[6], "最新的一份完整保留"

    print("compact ok")


def test_observer():
    """Observer 协议：CompositeObserver 分发、BaseObserver 空实现、真实实例继承契约。"""
    from observer import Observer, CompositeObserver, BaseObserver

    # ── CompositeObserver 分发到所有子观察者 ──
    calls = []
    class Spy(BaseObserver):
        def on_thinking(self, token): calls.append(("thinking", token))
        def on_delta(self, token): calls.append(("delta", token))
        def on_flush(self): calls.append(("flush",))
        def before_send(self, messages, model): calls.append(("before_send", len(messages), model))
        def save(self, messages): calls.append(("save", len(messages)))
        def display_msg(self, content): calls.append(("display_msg", content))

    comp = CompositeObserver([Spy(), Spy()])
    comp.on_thinking("t1")
    comp.on_delta("d1")
    comp.on_flush()
    comp.before_send([{"role": "user"}], "gpt-4")
    comp.save([{"role": "user"}])
    comp.display_msg("hello")

    assert len(calls) == 12, f"6 方法 × 2 观察者 = 12 次调用，实际 {len(calls)}"
    assert calls[0] == ("thinking", "t1") and calls[1] == ("thinking", "t1")

    # ── CompositeObserver 空列表不崩 ──
    empty = CompositeObserver([])
    empty.on_thinking("x")
    empty.on_delta("x")
    empty.on_flush()
    empty.before_send([], "")
    empty.save([])
    empty.display_msg("x")

    # ── BaseObserver 所有方法可调用不崩，且返回 None ──
    null = BaseObserver()
    null.on_thinking("x")
    null.on_delta("x")
    null.on_flush()
    null.before_send([], "")
    null.save([])
    null.display_msg("x")

    # ── 真实观察者实例继承 BaseObserver，具有全部 6 个方法 ──
    from display import spinner
    from compact import observer as compact_obs
    from history import observer as history_obs

    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    for name, obj in [("display.spinner", spinner),
                       ("compact.observer", compact_obs),
                       ("history.observer", history_obs)]:
        methods = {m for m in dir(obj) if not m.startswith("_") and callable(getattr(obj, m))}
        missing = required - methods
        assert not missing, f"{name} 缺少方法: {missing}"

    print("observer ok")


def test_websocket_observer():
    """WebSocketObserver：继承 BaseObserver，observer 方法序列化为 JSON 消息入队，
    before_send/save 空操作，所有方法非阻塞。"""
    from observer import BaseObserver
    from websocket_observer import WebSocketObserver
    import queue as q_module

    # ── 继承 BaseObserver ──
    obs = WebSocketObserver()
    assert isinstance(obs, BaseObserver), "WebSocketObserver 应继承 BaseObserver"

    # ── 6 个方法齐全 ──
    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    methods = {m for m in dir(obs) if not m.startswith("_") and callable(getattr(obs, m))}
    missing = required - methods
    assert not missing, f"缺少方法: {missing}"

    # ── messages / input_queue 属性暴露队列，类型为 Queue ──
    assert isinstance(obs.messages, q_module.Queue), "messages 应是 Queue 实例"
    assert isinstance(obs.input_queue, q_module.Queue), "input_queue 应是 Queue 实例"

    # ── on_thinking(token) → {"type": "thinking", "token": token} ──
    obs.on_thinking("思考中")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "thinking", "token": "思考中"}, f"on_thinking 消息错误: {msg}"

    # ── on_delta(token) → {"type": "delta", "token": token} ──
    obs.on_delta("hello")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "delta", "token": "hello"}, f"on_delta 消息错误: {msg}"

    # ── on_flush() → {"type": "flush"} ──
    obs.on_flush()
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "flush"}, f"on_flush 消息错误: {msg}"

    # ── display_msg(content) → {"type": "display", "content": content} ──
    obs.display_msg("hello world")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "display", "content": "hello world"}, f"display_msg 消息错误: {msg}"

    # ── before_send/save 空操作，不入队 ──
    obs.before_send([{"role": "user"}], "gpt-4")
    obs.save([{"role": "user"}])
    assert obs.messages.empty(), f"before_send/save 不应入队，但队列非空"

    # ── 顺序保证：多个调用的入队顺序正确 ──
    obs.on_thinking("t1")
    obs.on_delta("d1")
    obs.on_flush()
    expected = [
        {"type": "thinking", "token": "t1"},
        {"type": "delta", "token": "d1"},
        {"type": "flush"},
    ]
    for exp in expected:
        msg = obs.messages.get(timeout=0.1)
        assert msg == exp, f"顺序错误: 期望 {exp}, 实际 {msg}"

    # ── 非阻塞验证：入队立即返回（不抛异常即非阻塞） ──
    obs.on_delta("fast")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "delta", "token": "fast"}

    print("websocket_observer ok")


if __name__ == "__main__":
    # 自动扫本模块 test_* 函数按定义顺序执行；加测试只加 def test_xxx，不用改此段。
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    import tests_tools
    tests_tools.run_all()
    print("全部通过")
