"""后台任务管理：线程池执行、超时转后台、状态查询、取消。

设计哲学：极简，最小侵入，与 Result 三元组完全对齐。
借鉴 Claude Code：结果写文件、支持续等，不直接返回大结果爆 token。
"""

import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bg-task")
_tasks = {}  # task_id -> Future 对象
_results = {}  # task_id -> 结果文件路径
_lock = threading.Lock()


def _save_result(task_id, result):
    """把结果序列化到临时文件，返回路径，避免直接返回大结果爆 token。"""
    fd, path = tempfile.mkstemp(suffix=".txt", prefix=f"task-{task_id}-")
    try:
        os.write(fd, str(result).encode("utf-8"))
    finally:
        os.close(fd)
    with _lock:
        _results[task_id] = path
    return path


def run_with_timeout(fn, timeout=60, *args, **kwargs):
    """执行函数，超时返回任务ID，不中断任务。

    返回: (result, error, task_id)
        - 正常完成: (结果, None, None)
        - 超时: (None, TimeoutError, task_id)
        - 执行出错: (None, exception, None)
    """
    future = _executor.submit(fn, *args, **kwargs)
    task_id = str(id(future))

    with _lock:
        _tasks[task_id] = future

    try:
        result = future.result(timeout=timeout)
        return result, None, None
    except FutureTimeout:
        return None, TimeoutError(f"超过 {timeout} 秒"), task_id
    except Exception as e:
        return None, e, None


def task_status(task_id, wait=None):
    """查询任务状态，支持续等，返回 Result（与其他预置函数对齐）。

    wait: None=不续等直接返回，正数=最多续等N秒
    status: running / done / failed / cancelled
    任务完成时 result_path 字段含结果文件路径，用 read() 读取。
    """
    with _lock:
        future = _tasks.get(task_id)

    if future is None:
        from result import Result
        return Result(f"任务 {task_id} 不存在", error=KeyError(task_id), status="unknown")

    from result import Result

    if wait is not None and wait > 0:
        try:
            future.result(timeout=wait)
        except FutureTimeout:
            pass  # 续等也超时，继续返回状态
        except Exception:
            pass  # 执行出错，下面统一处理

    if future.cancelled():
        return Result("已取消", error=None, status="cancelled", task_id=task_id)
    if future.running():
        return Result("运行中", error=None, status="running", task_id=task_id)
    if future.done():
        try:
            result = future.result(timeout=0)
            path = _save_result(task_id, result)
            return Result(
                f"已完成，结果保存在: {path}\n用 read() 读取",
                error=None,
                status="done",
                task_id=task_id,
                result_path=path,
            )
        except Exception as e:
            path = _save_result(task_id, f"错误: {e}")
            return Result(
                f"执行失败: {e}\n详情保存在: {path}",
                error=e,
                status="failed",
                task_id=task_id,
                result_path=path,
            )

    return Result("未知状态", error=None, status="unknown", task_id=task_id)


def task_cancel(task_id):
    """取消后台任务，返回 Result（与其他预置函数对齐）。

    注意：线程取消是尽力而为，正在运行的线程可能无法立即终止。
    """
    with _lock:
        future = _tasks.get(task_id)

    if future is None:
        from result import Result
        return Result(f"任务 {task_id} 不存在", error=KeyError(task_id), status="unknown")

    cancelled = future.cancel()
    from result import Result

    if cancelled:
        return Result("已取消", error=None, status="cancelled", task_id=task_id)
    return Result("任务已在运行，无法取消（尽力而为）", error=None, status="running", task_id=task_id)
