"""预置函数 bg_start：把 fn 扔到后台 daemon 线程执行，返回 _BgThread 对象。"""

import threading


class _BgThread(threading.Thread):
    """后台线程，join() 返回函数返回值。"""

    def __init__(self, fn, args, kwargs):
        super().__init__(daemon=True)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._result = None

    def run(self):
        self._result = self._fn(*self._args, **self._kwargs)

    def join(self, timeout=None):
        super().join(timeout)
        return self._result


def bg_start(fn, *args, **kwargs):
    """把 fn(*args, **kwargs) 扔到后台 daemon 线程执行，立即返回 _BgThread 对象。

    后台运行，完成后不会主动通知——需主动调用 t.join() 等待线程结束并返回 fn 的返回值。
    """
    t = _BgThread(fn, args, kwargs)
    t.start()
    return t
