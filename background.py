"""后台任务层接口。实现见 _background.py。

run_with_timeout(fn, timeout=60, *args, **kwargs) -> (result, error, task_id)
    执行 fn(*args, **kwargs)；超过 timeout 秒转后台继续运行。三种返回姿势：
        正常完成:   (result, None, None)
        超时转后台: (None, TimeoutError, task_id)  fn 继续后台执行。
        执行出错:   (None, exception, None)

task_status(task_id, wait=None) -> Result
    查询状态；wait 非 None 时最多续等 wait 秒。
    Result.status ∈ {running, done, failed, cancelled, unknown}。
    完成态（done / failed）附 result_path=<文件路径>；消费者用 read(result_path) 读结果
    （大结果不直接返回，避免爆 token）。
    task_id 不存在时 status='unknown'，error=KeyError。

task_cancel(task_id) -> Result
    尽力停止后台任务；正在运行的线程无法立即终止。
    Result.status ∈ {cancelled, running, unknown}。

task_id 对消费者不透明：仅作句柄传递，不解析结构。
"""
from _background import run_with_timeout, task_status, task_cancel
