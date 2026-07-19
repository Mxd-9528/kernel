"""WebSocket 传输适配器：继承 ProtocolObserver 的 JSON-RPC 序列化，
同时提供上行通道（input_queue、interrupt_event）。

调用者（agent 循环）调用 observer 方法后立即返回，不感知网络边界。
chat() 通过 input_source=lambda: observer.input_queue.get() 读取用户输入。
浏览器发送 {"jsonrpc":"2.0","method":"chat/interrupt"} 时，server 设置 interrupt_event，
agent 循环每轮检查此事件终止生成。

序列化逻辑来自 ProtocolObserver（内核 Port），本适配器只负责上行通道（Adapter）。
"""
from ..observer import ProtocolObserver
from queue import Queue
from threading import Event


class WebSocketObserver(ProtocolObserver):
    """WebSocket 传输适配器：输出继承 ProtocolObserver 的 JSON-RPC 序列化，
    输入提供 input_queue + interrupt_event 上行通道。

    前置条件：无（构造时不依赖任何外部资源）
    后置条件：
      - messages: 继承自 ProtocolObserver，后台线程消费此队列，通过 WebSocket 广播
      - input_queue: 服务端收到浏览器消息后写入，chat() 的 input_source 从此读取
      - interrupt_event: 浏览器发送中断消息时设置，chat() 监听以终止生成
    不变量：所有 observer 方法 O(1) 入队，不阻塞。
    """

    def __init__(self):
        super().__init__()
        self.input_queue = Queue()
        self.interrupt_event = Event()
