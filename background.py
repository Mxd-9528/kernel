"""后台任务层接口。实现见 _background.py。

run_with_timeout(fn, timeout=60, *args, **kwargs) -> (result, error, task_id)
    执行 fn(*args, **kwargs)；超过 timeout 秒转后台继续运行。三种返回姿势：
        正常完成:   (原始返回值, None, None)
        超时转后台: (None, TimeoutError, task_id)  fn 继续后台执行。
        执行出错:   (None, exception, None)

task_status(task_id, wait=None) -> (state, payload)
    查询任务状态。返回原始状态元组，由上层（如 tools/task_status.py）包装成 dict。
    state ∈ {"running","done","failed","cancelled","unknown"}
    payload 语义：
      done → 任务原始返回值（任意 Python 类型）
      failed → 原始异常对象
      running / cancelled / unknown → None
    wait 非 None 时最多续等 wait 秒。

task_cancel(task_id) -> state
    尽力停止后台任务；正在运行的线程无法立即终止（Python 线程限制）。
    state ∈ {"cancelled","running","unknown"}

task_id 对消费者不透明：仅作句柄传递，不解析结构。
"""
from _background import run_with_timeout, task_status, task_cancel
