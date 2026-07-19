"""观察者协议：agent 循环通过这 5 个显示方法通知外部（纯显示契约）。

Observer 定义协议，BaseObserver 提供空实现（GoF Adapter 模式）。
本文件不依赖任何模块，所有模块依赖它。
"""
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
