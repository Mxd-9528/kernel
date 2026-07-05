"""预置函数 bash：执行 shell 命令，返回 stdout + returncode 三元组。

契约：命令退出码非0是「被调程序的业务结果」→ 进 .facts，bash 工具自身 error=None；
只有 bash 启动不了或超时才算工具失败 → error 承载。

stdout 实时刷入临时文件（避免 subprocess.PIPE 缓冲区吞输出的问题），
stdout_file 进 facts；模型可后续 read(stdout_file) 拿完整累积。stderr 合并到 stdout（按时序）。
"""

import os
import shutil
import subprocess
import tempfile

from result import Result

_GIT_BASH = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
]


def _bash_exe():
    return shutil.which("bash") or next((p for p in _GIT_BASH if shutil.which(p)), "bash")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().rstrip("\r\n")


def bash(command, timeout=30, cwd=None):
    """执行 shell 命令（Git Bash/POSIX），stdout 落临时文件并返回内容。

    timeout: 硬超时秒数。到时未完成即杀进程 + error=TimeoutExpired。默认 30。
    stdout_file: 所有调用都落进 facts，模型可 read(stdout_file) 拿完整输出（超时后也可用）。

    .error 只在 bash 自身没跑成时非 None（找不到 bash、超时）；命令退出码非零是命令的业务失败、
    不是 bash 工具的失败，所以 .error 仍是 None——想知道命令成败查 .returncode（facts），不是 .error。
    """
    fd, log_path = tempfile.mkstemp(suffix=".log", prefix="bash-")
    try:
        p = subprocess.Popen(
            [_bash_exe(), "-lc", command],
            stdout=fd, stderr=subprocess.STDOUT, cwd=cwd,
        )
    finally:
        os.close(fd)  # 我们不读文件描述符，subprocess 独占它写

    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        return Result(
            _read(log_path),
            error=subprocess.TimeoutExpired(command, timeout),
            returncode=None,
            timeout=timeout,
            stdout_file=log_path,
        )

    return Result(
        _read(log_path),
        error=None,
        returncode=p.returncode,
        stdout_file=log_path,
    )
