"""预置函数 bg_start：把 fn 扔到后台 daemon 线程执行，返回 threading.Thread 对象。"""

import threading


def bg_start(fn, *args, **kwargs):
    """把 fn(*args, **kwargs) 扔到后台 daemon 线程执行，立即返回 threading.Thread 对象。"""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
