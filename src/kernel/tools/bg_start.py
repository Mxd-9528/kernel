"""预置函数 bg_start：把 fn 扔到后台 daemon 线程执行，返回 Future。"""

from __future__ import annotations

import threading
from concurrent.futures import Future
from typing import Callable, TypeVar

T = TypeVar("T")


def bg_start(fn: Callable[..., T], *args, **kwargs) -> Future[T]:
    """把 fn(*args, **kwargs) 扔到后台 daemon 线程执行，立即返回 Future。

    后台运行，完成后不会主动通知——需主动调用 f.result() 等待并返回 fn 的返回值。
    fn 抛出的异常在 f.result() 处重新抛出。
    """
    fut: Future[T] = Future()

    def target() -> None:
        if not fut.set_running_or_notify_cancel():
            return
        try:
            fut.set_result(fn(*args, **kwargs))
        except BaseException as e:
            fut.set_exception(e)

    threading.Thread(target=target, daemon=True).start()
    return fut
