"""compact 模块测试。"""



def test_compact():
    """compact 未过阈值原样返回，过阈值 mock 压缩验证重组。"""
    from kernel.compact import compact

    def conv(n):
        h = [{"role": "system", "content": "sys"}]
        for i in range(n):
            h.append({"role": "user", "content": f"u{i}"})
            h.append({"role": "assistant", "content": f"a{i}"})
        return h

    from kernel import compact as compact_mod
    big = conv(10)
    old_func = compact_mod.stream_chat
    compact_mod.stream_chat = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("不该调用"))
    try:
        assert compact(big, keep=6, threshold=1_000_000) == big
    finally:
        compact_mod.stream_chat = old_func

    compact_mod.stream_chat = lambda *a, **kw: iter([("content", "【摘要】")])
    try:
        new = compact(conv(10), keep=6, threshold=1)
        assert new[0] == {"role": "system", "content": "sys"}
        assert any(m["role"] == "assistant" and "【摘要】" in m["content"] for m in new)
        assert new[-1] == {"role": "assistant", "content": "a9"}
        assert len(new) < len(conv(10))
    finally:
        compact_mod.stream_chat = old_func
    print("compact ok")


def test_split_history():
    """split_history 按 assistant 轮数切分。"""
    from kernel.compact import split_history

    def conv(n):
        h = [{"role": "system", "content": "sys"}]
        for i in range(n):
            h.append({"role": "user", "content": f"u{i}"})
            h.append({"role": "assistant", "content": f"a{i}"})
        return h

    h = conv(10)
    system, mid, recent = split_history(h, keep=6)
    assert system == [{"role": "system", "content": "sys"}]
    assert sum(1 for m in recent if m["role"] == "assistant") == 6
    assert sum(1 for m in mid if m["role"] == "assistant") == 4
    assert system + mid + recent == h
    print("split_history ok")


def test_dedup_tool_outputs():
    """重复 [环境反馈] 内容旧的替换为引用行，最新保留。"""
    from kernel.compact import _dedup_tool_outputs

    mid = [
        {"role": "user", "content": "[环境反馈] hello"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "[环境反馈] hello"},
        {"role": "assistant", "content": "ok2"},
        {"role": "user", "content": "[环境反馈] different"},
        {"role": "assistant", "content": "ok3"},
        {"role": "user", "content": "[环境反馈] hello"},
    ]
    out = _dedup_tool_outputs(list(mid))
    assert out[0]["content"].startswith("[环境反馈同下文")
    assert out[2]["content"].startswith("[环境反馈同下文")
    assert out[4] == mid[4]
    assert out[6] == mid[6]
    print("dedup_tool_outputs ok")


def test_compact_observer():
    from kernel.observer import BaseObserver
    from kernel.compact import observer
    assert isinstance(observer, BaseObserver)
    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    methods = {m for m in dir(observer) if not m.startswith("_") and callable(getattr(observer, m))}
    missing = required - methods
    assert not missing, f"compact.observer 缺少方法: {missing}"
    print("compact_observer ok")
