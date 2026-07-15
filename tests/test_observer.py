"""observer 模块测试。"""


def test_composite_observer():
    from kernel.observer import BaseObserver, CompositeObserver

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

    assert len(calls) == 12, f"6 方法 x 2 观察者 = 12 次调用，实际 {len(calls)}"
    assert calls[0] == ("thinking", "t1") and calls[1] == ("thinking", "t1")

    empty = CompositeObserver([])
    empty.on_thinking("x")
    empty.on_delta("x")
    empty.on_flush()
    empty.before_send([], "")
    empty.save([])
    empty.display_msg("x")

    null = BaseObserver()
    null.on_thinking("x")
    null.on_delta("x")
    null.on_flush()
    null.before_send([], "")
    null.save([])
    null.display_msg("x")

    from kernel.display import spinner
    from kernel.compact import observer as compact_obs
    from kernel.history import observer as history_obs

    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    for name, obj in [("display.spinner", spinner),
                       ("compact.observer", compact_obs),
                       ("history.observer", history_obs)]:
        methods = {m for m in dir(obj) if not m.startswith("_") and callable(getattr(obj, m))}
        missing = required - methods
        assert not missing, f"{name} 缺少方法: {missing}"

    print("observer ok")
