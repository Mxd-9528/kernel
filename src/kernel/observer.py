"""观察者协议：agent 循环通过这 5 个显示方法通知外部（纯显示契约）。

Observer 定义协议，BaseObserver 提供空实现（GoF Adapter 模式）。
ProtocolObserver 提供语言无关的 JSON-RPC 序列化（Port，六边形架构）。
WebSocket / stdio / display.py 等传输适配器从 messages 队列消费同一份 dict。
本文件不依赖任何模块，所有模块依赖它。
"""
from queue import Queue
from typing import Protocol


class Observer(Protocol):
    """纯显示协议：agent 循环通过这 5 个方法通知显示层。"""
    def on_thinking(self, token: str) -> None: ...
    def on_delta(self, token: str) -> None: ...
    def on_flush(self, text: str = "") -> None: ...
    def on_user(self, text: str) -> None: ...
    def display_msg(self, content: str) -> None: ...


class BaseObserver:
    """观察者基类：所有方法默认为空。子类只覆盖关心的方法（GoF Adapter 模式）。"""
    def on_thinking(self, token: str) -> None: pass
    def on_delta(self, token: str) -> None: pass
    def on_flush(self, text: str = "") -> None: pass
    def on_user(self, text: str) -> None: pass
    def display_msg(self, content: str) -> None: pass


class ProtocolObserver(BaseObserver):
    """协议端口：5 个显示方法 → JSON-RPC 2.0 notification dict 入队。

    前置条件：无
    后置条件：
      - self.messages 是 queue.Queue 实例
      - 每个方法调用产出一个 JSON-RPC dict 入队
    不变量：messages 队列只包含合法的 JSON-RPC 2.0 notification dict。
    传输适配器（WebSocket / stdio）从 messages 队列消费 dict，不自己序列化。
    """

    def __init__(self) -> None:
        self.messages: Queue = Queue()

    def on_thinking(self, token: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/thinking",
                          "params": {"token": token}})

    def on_delta(self, token: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/delta",
                          "params": {"token": token}})

    def on_flush(self, text: str = "") -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/flush",
                          "params": {"text": text}})

    def on_user(self, text: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/user",
                          "params": {"content": text}})

    def display_msg(self, content: str) -> None:
        self.messages.put({"jsonrpc": "2.0", "method": "window/display",
                          "params": {"content": content}})
