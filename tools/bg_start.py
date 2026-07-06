"""预置函数 bg_start：把函数扔到后台线程执行，返回 threading.Thread 对象。

用例：模型想让长任务在后台跑，主循环继续做别的（如：下载大文件、跑长测试、
监听消息）。用 Python 标准 threading.Thread——查询用 t.is_alive() / t.join(timeout=N)。

共享数据通过闭包变量或全局变量传递——IPython 持久内核跨轮保留变量，
函数在后台线程里往列表 append 结果，主线程下一轮直接看该列表即可。

Python 线程无法外部强杀——想让后台任务停下，靠共享变量协作（如 stop_flag=True）。
"""

import threading


def bg_start(fn, *args, **kwargs):
    """把 fn(*args, **kwargs) 扔到后台 daemon 线程执行，立即返回 threading.Thread 对象。

    示例：
        results = []
        def worker():
            import time
            for i in range(10):
                time.sleep(1)
                results.append(i)
        t = bg_start(worker)
        # 主线程/下一轮继续做别的
        # 稍后查看：t.is_alive() 判断是否还在跑；results 看进度
    """
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
