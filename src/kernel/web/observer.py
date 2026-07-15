"""WebSocket 观察者：把 observer 事件序列化为 JSON 消息，放入输出队列；
同时提供输入队列，接收来自浏览器的用户输入。

调用者（agent 循环）调用 observer 方法后立即返回，不感知网络边界。
chat() 通过 input_source=lambda: observer.input_queue.get() 读取用户输入。
"""
from ..observer import BaseObserver
from queue import Queue


class WebSocketObserver(BaseObserver):
    """观察者实现：输出 → messages 队列，输入 → input_queue。

    前置条件：无（构造时不依赖任何外部资源）
    后置条件：
      - messages: 后台线程消费此队列，通过 WebSocket 广播
      - input_queue: 服务端收到浏览器消息后写入，chat() 的 input_source 从此读取
      - before_send / save：空操作（压缩和持久化在服务端完成）
    不变量：所有 observer 方法 O(1) 入队，不阻塞。
    """

    def __init__(self):
        self.messages = Queue()
        self.input_queue = Queue()

    def on_thinking(self, token: str) -> None:
        self.messages.put({"type": "thinking", "token": token})

    def on_delta(self, token: str) -> None:
        self.messages.put({"type": "delta", "token": token})

    def on_flush(self) -> None:
        self.messages.put({"type": "flush"})

    def display_msg(self, content: str) -> None:
        self.messages.put({"type": "display", "content": content})
