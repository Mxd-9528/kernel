"""查询后台任务状态，支持续等。

wait: None=不续等直接返回，正数=最多续等N秒
返回 status: running / done / failed / cancelled
任务完成时 result_path 字段含结果文件路径，用 read() 读取。
"""

from background_contract import task_status as _task_status


def task_status(task_id, wait=None):
    """查询后台任务状态，wait=N 最多续等N秒。"""
    return _task_status(task_id, wait)
