"""后台任务管理：ThreadPoolExecutor + Future 生命周期。

只管线程/Future，不构造反馈载体，不落盘——反馈由上层
（tools/task_status.py, tools/task_cancel.py）按需构造 dict / str。
"""

import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bg-task")
_tasks = {}  # task_id -> Future
_lock = threading.Lock()


def run_with_timeout(fn, timeout=60, *args, **kwargs):
    """执行 fn(*args, **kwargs)；超过 timeout 秒转后台。

    返回: (result, error, task_id)
        - 正常完成: (原始返回值, None, None)
        - 超时: (None, TimeoutError, task_id)  fn 继续后台执行
        - 执行出错: (None, exception, None)
    """
    future = _executor.submit(fn, *args, **kwargs)
    task_id = str(id(future))
    with _lock:
        _tasks[task_id] = future

    try:
        return future.result(timeout=timeout), None, None
    except FutureTimeout:
        return None, TimeoutError(f"超过 {timeout} 秒"), task_id
    except Exception as e:
        return None, e, None


def task_status(task_id, wait=None):
    """查询任务状态。返回 (state, payload) 原始状态元组，由上层包装。

    state ∈ {"running","done","failed","cancelled","unknown"}
    payload 语义：
      done → 任务原始返回值（任意 Python 类型）
      failed → 原始异常对象
      running/cancelled/unknown → None
    wait: None=不续等；正数=最多续等 N 秒
    """
    with _lock:
        future = _tasks.get(task_id)
    if future is None:
        return "unknown", None

    if wait is not None and wait > 0:
        try:
            future.result(timeout=wait)
        except (FutureTimeout, Exception):
            pass  # 续等超时或执行出错，走下面统一处理

    if future.cancelled():
        return "cancelled", None
    if future.running():
        return "running", None
    if future.done():
        try:
            return "done", future.result(timeout=0)
        except Exception as e:
            return "failed", e
    return "unknown", None


def task_cancel(task_id):
    """尽力取消。返回 state ∈ {"cancelled","running","unknown"}。

    Python 线程不能外部强杀——已在跑的任务无法取消。
    """
    with _lock:
        future = _tasks.get(task_id)
    if future is None:
        return "unknown"
    return "cancelled" if future.cancel() else "running"
