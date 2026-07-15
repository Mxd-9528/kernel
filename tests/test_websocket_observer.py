"""WebSocket Observer 测试。"""

import queue as q_module


def test_websocket_observer():
    from kernel.observer import BaseObserver
    from kernel.web.observer import WebSocketObserver

    obs = WebSocketObserver()
    assert isinstance(obs, BaseObserver)

    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    methods = {m for m in dir(obs) if not m.startswith("_") and callable(getattr(obs, m))}
    missing = required - methods
    assert not missing, f"缺少方法: {missing}"

    assert isinstance(obs.messages, q_module.Queue)
    assert isinstance(obs.input_queue, q_module.Queue)

    obs.on_thinking("thinking")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "thinking", "token": "thinking"}

    obs.on_delta("hello")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "delta", "token": "hello"}

    obs.on_flush()
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "flush"}

    obs.display_msg("hello world")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "display", "content": "hello world"}

    obs.before_send([{"role": "user"}], "gpt-4")
    obs.save([{"role": "user"}])
    assert obs.messages.empty()

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

    obs.on_delta("fast")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"type": "delta", "token": "fast"}

    print("websocket_observer ok")
