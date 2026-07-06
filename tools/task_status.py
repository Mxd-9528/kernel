"""查询后台任务状态，支持续等。

wait: None=不续等直接返回，正数=最多续等N秒
返回 Result：facts.status ∈ {running / done / failed / cancelled / unknown}。
完成时若原始返回值是 Result（如 _run_cell 的产物），原 facts 完整保留；
否则包一层字符串化的 Result。
"""

from background import task_status as _task_status
from result import Result


def task_status(task_id, wait=None):
    """查询后台任务状态，wait=N 最多续等N秒。原 Result 的 facts 完整保真。"""
    state, payload = _task_status(task_id, wait)

    if state == "unknown":
        return Result(f"任务 {task_id} 不存在", error=KeyError(task_id), status="unknown")
    if state == "cancelled":
        return Result("已取消", error=None, status="cancelled", task_id=task_id)
    if state == "running":
        return Result("运行中", error=None, status="running", task_id=task_id)
    if state == "failed":
        return Result("", error=payload, status="failed", task_id=task_id)

    # state == "done"：payload 是任务原始返回值
    if isinstance(payload, Result):
        # 已是 Result（如 _run_cell 或预置函数的产物）——加 task_id/status 到 facts 后透传
        payload.facts["task_id"] = task_id
        payload.facts["status"] = "done"
        return payload
    # 非 Result（模型直接 run_with_timeout 跑纯 Python 函数）——包一层
    return Result(str(payload), error=None, status="done", task_id=task_id)
