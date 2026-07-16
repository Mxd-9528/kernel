"""WebSocket 观察者：把 observer 事件序列化为 JSON 消息，放入输出队列；
同时提供输入队列，接收来自浏览器的用户输入。

调用者（agent 循环）调用 observer 方法后立即返回，不感知网络边界。
chat() 通过 input_source=lambda: observer.input_queue.get() 读取用户输入。
浏览器发送 {"jsonrpc":"2.0","method":"chat/interrupt"} 时，server 设置 interrupt_event，
agent 循环每轮检查此事件终止生成。
"""
from ..observer import BaseObserver
from queue import Queue
from threading import Event


class WebSocketObserver(BaseObserver):
    """观察者实现：输出 → messages 队列，输入 → input_queue。

    前置条件：无（构造时不依赖任何外部资源）
    后置条件：
      - messages: 后台线程消费此队列，通过 WebSocket 广播
      - input_queue: 服务端收到浏览器消息后写入，chat() 的 input_source 从此读取
      - interrupt_event: 浏览器发送中断消息时设置，chat() 监听以终止生成
      - before_send / save：空操作（压缩和持久化在服务端完成）
    不变量：所有 observer 方法 O(1) 入队，不阻塞。
    """

    def __init__(self):
        self.messages = Queue()
        self.input_queue = Queue()
        self.interrupt_event = Event()

    def on_thinking(self, token: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/thinking",
                          "params": {"token": token}})

    def on_delta(self, token: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/delta",
                          "params": {"token": token}})

    def on_flush(self) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/flush",
                          "params": {}})

    def on_user(self, text: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/user",
                          "params": {"content": text}})

    def display_msg(self, content: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/display",
                          "params": {"content": content}})
