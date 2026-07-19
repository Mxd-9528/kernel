"""ProtocolObserver 测试：协议序列化 → JSON-RPC dict 入队。

TDD 红灯：ProtocolObserver 尚未实现，此测试应失败。
"""

from queue import Queue


def test_protocol_observer_creates_queue():
    """ProtocolObserver 构造时创建 messages 队列。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    assert isinstance(proto.messages, Queue)


def test_protocol_observer_on_delta():
    """on_delta → window/delta JSON-RPC dict 入队。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.on_delta("hello")
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/delta", "params": {"token": "hello"}}


def test_protocol_observer_on_thinking():
    """on_thinking → window/thinking JSON-RPC dict 入队。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.on_thinking("reasoning...")
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/thinking", "params": {"token": "reasoning..."}}


def test_protocol_observer_on_flush():
    """on_flush → window/flush JSON-RPC dict 入队，含 text 参数。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.on_flush("full text")
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/flush", "params": {"text": "full text"}}


def test_protocol_observer_on_flush_default():
    """on_flush 无参时 text 为空字符串。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.on_flush()
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/flush", "params": {"text": ""}}


def test_protocol_observer_on_user():
    """on_user → window/user JSON-RPC dict 入队。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.on_user("user input")
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/user", "params": {"content": "user input"}}


def test_protocol_observer_display_msg():
    """display_msg → window/display JSON-RPC dict 入队。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    proto.display_msg("system message")
    msg = proto.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/display", "params": {"content": "system message"}}


def test_protocol_observer_all_five_methods():
    """ProtocolObserver 恰好 5 个显示方法，无 before_send/save。"""
    from kernel.observer import ProtocolObserver
    proto = ProtocolObserver()
    required = {"on_thinking", "on_delta", "on_flush", "on_user", "display_msg"}
    methods = {m for m in dir(proto) if not m.startswith("_") and callable(getattr(proto, m))}
    # messages 队列属性不算方法
    methods.discard("messages")
    missing = required - methods
    extra = methods - required
    assert not missing, f"缺失方法: {missing}"
    assert not extra, f"多余方法: {extra}"
    assert "before_send" not in methods
    assert "save" not in methods


def test_websocket_observer_inherits_protocol():
    """WebSocketObserver 继承 ProtocolObserver 的序列化，不再自己覆盖。"""
    from kernel.web.observer import WebSocketObserver
    from kernel.observer import ProtocolObserver
    ws = WebSocketObserver()
    # 必须是 ProtocolObserver 的子类
    assert isinstance(ws, ProtocolObserver)
    # 仍有上行通道
    from queue import Queue
    assert isinstance(ws.input_queue, Queue)
    assert hasattr(ws, "interrupt_event")
    # 序列化行为继承自 ProtocolObserver
    ws.on_delta("test")
    msg = ws.messages.get(timeout=0.1)
    assert msg == {"jsonrpc": "2.0", "method": "window/delta", "params": {"token": "test"}}


def test_server_import_compatible():
    """server.py 的 import 不受影响。"""
    import kernel.web.server  # 不报错
    assert kernel.web.server is not None
