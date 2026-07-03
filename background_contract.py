"""background 合同 —— 沉淀线，上游读这份即可，不下潜 background.py。

def run_with_timeout(fn, timeout=60, *args, **kwargs) -> (result, error, task_id):
    执行 fn，三种返回姿势（消费者按此顺序判）：
      正常完成: (result, None, None)
      超时转后台: (None, TimeoutError, task_id)   —— fn 继续在后台跑
      执行出错: (None, exception, None)

def task_status(task_id, wait=None) -> Result:
    查询状态，可选续等 wait 秒。
    Result.status ∈ {running, done, failed, cancelled, unknown}
    完成时（done/failed）附字段 result_path=<文件路径>，
      跨层协议：消费者用 read(result_path) 读结果，不直接返回大结果避免爆 token。
    task_id 不存在时 status='unknown'，error=KeyError。

def task_cancel(task_id) -> Result:
    尽力而为：正在运行的线程无法立即终止。
    Result.status ∈ {cancelled, running, unknown}

task_id 不透明：消费者不得解析其结构，只作为句柄传递。
"""
from background import run_with_timeout, task_status, task_cancel
