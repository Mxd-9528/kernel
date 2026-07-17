"""观察者协议：agent 循环通过这 6 个方法通知外部。

Observer Protocol 定义契约，BaseObserver 提供空实现（GoF Adapter 模式），
CompositeObserver 把多个观察者组合成一个。所有模块依赖此文件，此文件不依赖任何模块。
"""
from typing import Protocol


class Observer(Protocol):
    """观察者协议：agent 循环通过这 7 个方法通知外部。"""
    def on_thinking(self, token: str) -> None: ...
    def on_delta(self, token: str) -> None: ...
    def on_flush(self) -> None: ...
    def on_user(self, text: str) -> None: ...
    def before_send(self, messages: list, model: str | None) -> None: ...
    def save(self, messages: list) -> None: ...
    def display_msg(self, content: str) -> None: ...


class CompositeObserver:
    """把多个观察者组合成一个，调用时分发到每个。"""

    def __init__(self, observers: list[Observer]) -> None:
        self._observers = observers

    def on_thinking(self, token: str) -> None:
        for o in self._observers:
            o.on_thinking(token)

    def on_delta(self, token: str) -> None:
        for o in self._observers:
            o.on_delta(token)

    def on_flush(self) -> None:
        for o in self._observers:
            o.on_flush()

    def on_user(self, text: str) -> None:
        for o in self._observers:
            o.on_user(text)

    def before_send(self, messages: list, model: str | None) -> None:
        for o in self._observers:
            o.before_send(messages, model)

    def save(self, messages: list) -> None:
        for o in self._observers:
            o.save(messages)

    def display_msg(self, content: str) -> None:
        for o in self._observers:
            o.display_msg(content)


class BaseObserver:
    """观察者基类：所有方法默认为空。子类覆盖关心的方法，其余继承空实现。

    模式来自 Java AWT MouseAdapter（GoF Adapter 模式）：接口有 N 个方法，
    基类提供 N 个空实现，消费者只覆盖自己关心的。"""
    def on_thinking(self, token: str) -> None: pass
    def on_delta(self, token: str) -> None: pass
    def on_flush(self) -> None: pass
    def on_user(self, text: str) -> None: pass
    def before_send(self, messages: list, model: str | None) -> None: pass
    def save(self, messages: list) -> None: pass
    def display_msg(self, content: str) -> None: pass
