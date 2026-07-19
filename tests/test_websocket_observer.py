"""WebSocket Observer 测试。"""

import queue as q_module


def test_websocket_observer():
    from kernel.observer import BaseObserver
    from kernel.web.observer import WebSocketObserver

    obs = WebSocketObserver()
    assert isinstance(obs, BaseObserver)

    required = {"on_thinking", "on_delta", "on_flush", "on_user", "display_msg"}
    methods = {m for m in dir(obs) if not m.startswith("_") and callable(getattr(obs, m))}
    missing = required - methods
    assert not missing, f"缺少方法: {missing}"

    assert isinstance(obs.messages, q_module.Queue)
    assert isinstance(obs.input_queue, q_module.Queue)

    obs.on_thinking("thinking")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/thinking", "params": {"token": "thinking"}}

    obs.on_delta("hello")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/delta", "params": {"token": "hello"}}

    obs.on_flush("hello")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/flush", "params": {"text": "hello"}}

    obs.display_msg("hello world")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/display", "params": {"content": "hello world"}}

    obs.on_thinking("t1")
    obs.on_delta("d1")
    obs.on_flush("d1")
    expected = [
        {"jsonrpc": "2.0", "method": "window/thinking", "params": {"token": "t1"}},
        {"jsonrpc": "2.0", "method": "window/delta", "params": {"token": "d1"}},
        {"jsonrpc": "2.0", "method": "window/flush", "params": {"text": "d1"}},
    ]
    for exp in expected:
        msg = obs.messages.get(timeout=0.1)
        assert msg == exp, f"顺序错误: 期望 {exp}, 实际 {msg}"

    obs.on_delta("fast")
    msg = obs.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/delta", "params": {"token": "fast"}}

    print("websocket_observer ok")
