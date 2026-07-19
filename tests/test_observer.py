"""observer 模块测试：纯显示协议（5 方法），BaseObserver 空实现。"""


def test_base_observer_five_methods():
    """Observer 协议收敛为 5 个纯显示方法；BaseObserver 提供空实现。"""
    from kernel.observer import BaseObserver

    required = {"on_thinking", "on_delta", "on_flush", "on_user", "display_msg"}
    methods = {m for m in dir(BaseObserver) if not m.startswith("_") and callable(getattr(BaseObserver, m))}
    assert methods == required, f"应恰好 5 个显示方法，实际 {methods}"

    # 后端逻辑（before_send/save）已剥离，不应再是 Observer 方法
    assert "before_send" not in methods
    assert "save" not in methods


def test_base_observer_noop():
    """BaseObserver 所有方法为空实现，可安全调用。"""
    from kernel.observer import BaseObserver

    o = BaseObserver()
    o.on_thinking("x")
    o.on_delta("x")
    o.on_flush()          # 无参兼容
    o.on_flush("full")    # 带 text
    o.on_user("x")
    o.display_msg("x")
    print("base_observer ok")


def test_on_flush_text_optional():
    """on_flush 的 text 参数可选（默认参数），新旧调用都不崩。"""
    import inspect
    from kernel.observer import BaseObserver

    sig = inspect.signature(BaseObserver.on_flush)
    assert sig.parameters["text"].default == "", "text 应有默认值 '' 以兼容无参调用"
    print("on_flush_text_optional ok")
