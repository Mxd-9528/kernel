"""取消后台任务（尽力而为）。

正在运行的线程可能无法立即终止。
"""

from background_contract import task_cancel as _task_cancel


def task_cancel(task_id):
    """取消后台任务（尽力而为）。"""
    return _task_cancel(task_id)
