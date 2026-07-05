"""代码执行层接口。实现见 _run.py。

run(code) -> Result
    在持久内核中执行 code 字符串，返回统一 Result 三元组。
    code: 一段 Python 源码（表达式或多语句，IPython cell 语义）。

    三种返回姿势（按 .error / facts.status 判）：
        正常完成:   Body = 末表达式 repr 或 stdout(strip)；.error = None；[facts.stderr]。
        执行出错:   Body = ""；.error = 原生异常；facts.stdout = traceback（已清 ANSI）；[facts.stderr]。
        超时转后台 (>60s):
            Body = 引导文本；.error = TimeoutError；
            facts.task_id = <句柄>；facts.status = "background"；
            后续用 background.task_status / task_cancel。

    透传: code 若本身返回 Result / ListResult / DictResult，原样透传。
    Side effects: 首次调用触发 IPython InteractiveShell 单例化并 inject(sh)（幂等）；
                  同进程内所有 run 调用共享同一命名空间。
"""
from _run import run
