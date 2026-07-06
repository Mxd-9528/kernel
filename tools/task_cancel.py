"""取消后台任务（尽力而为），返回 state 字符串。

Python 线程不能外部强杀——已在跑的任务只能等它自然完成或到达 checkpoint。
"""

from background import task_cancel as _task_cancel


def task_cancel(task_id):
    """取消后台任务（尽力而为）。返回 state ∈ {"cancelled","running","unknown"}。"""
    return _task_cancel(task_id)
