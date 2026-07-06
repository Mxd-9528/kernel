"""取消后台任务（尽力而为）。

Python 线程不能外部强杀——已在跑的任务只能等它自然完成或到达 checkpoint。
"""

from background import task_cancel as _task_cancel
from result import Result


def task_cancel(task_id):
    """取消后台任务（尽力而为）。"""
    state = _task_cancel(task_id)
    if state == "unknown":
        return Result(f"任务 {task_id} 不存在", error=KeyError(task_id), status="unknown")
    if state == "cancelled":
        return Result("已取消", error=None, status="cancelled", task_id=task_id)
    return Result("任务已在运行，无法取消（尽力而为）", error=None, status="running", task_id=task_id)
