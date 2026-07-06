"""查询后台任务状态，返回 dict。

state ∈ {"running", "done", "failed", "cancelled", "unknown"}
done 时 payload 是任务原始返回值；failed 时 payload 是原始异常对象。
"""

from background import task_status as _task_status


def task_status(task_id, wait=None):
    """查询后台任务状态。返回 dict：{"state": str, "payload": Any, "task_id": str}。

    state:
      done → payload 是任务原始返回值（任意 Python 类型）
      failed → payload 是原始异常对象
      running / cancelled / unknown → payload 为 None
    wait: None=不续等直接返回，正数=最多续等N秒
    """
    state, payload = _task_status(task_id, wait)
    return {"state": state, "payload": payload, "task_id": task_id}
