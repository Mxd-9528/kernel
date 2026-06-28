"""预置函数 bash：执行 shell 命令，返回 stdout + returncode 三元组。

契约：命令退出码非0是「被调程序的业务结果」→ 进 .facts，bash 工具自身 error=None；
只有 bash 启动不了或超时才算工具失败 → error 承载。
砍掉后台任务管理（task_id/日志/状态/进程树杀，~200行）——
subprocess.run(timeout=) 标准库自带超时+杀子进程+捕获，前台够用。后台真需要再说。
"""

import shutil
import subprocess

from result import Result

_GIT_BASH = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
]


def _bash_exe():
    return shutil.which("bash") or next((p for p in _GIT_BASH if shutil.which(p)), "bash")


def bash(command, timeout=30, cwd=None):
    """执行 shell 命令（Git Bash/POSIX），返回 stdout。timeout 秒，cwd 工作目录。

    .error 只在 bash 自身没跑成时非 None（找不到 bash、超时）；命令的退出码非零是命令的失败、
    不是 bash 工具的失败，所以 .error 仍是 None——想知道命令成败查 .returncode（facts），不是 .error。
    """
    try:
        p = subprocess.run(
            [_bash_exe(), "-lc", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=cwd,
        )
    except subprocess.TimeoutExpired as e:
        return Result(f"超时（{timeout}s）已终止", error=e, returncode=None, timeout=timeout)

    out = p.stdout.rstrip("\r\n")
    # returncode 是被调程序的业务结果，进 facts；bash 工具自身没故障 → error=None
    return Result(out, error=None, returncode=p.returncode, stderr=p.stderr.rstrip("\r\n"))
