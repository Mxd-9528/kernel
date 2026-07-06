"""预置函数 bash：执行 shell 命令，返回 subprocess.CompletedProcess。

标准库类型：CompletedProcess 有 .stdout / .stderr / .returncode / .args 属性。
stderr 合并到 stdout（按时序）。命令退出码非零不是失败——只是业务结果，通过 .returncode 判断。
超时通过 raise subprocess.TimeoutExpired 传递（含 .stdout 属性可看已收集输出）。
"""

import os
import shutil
import subprocess
import tempfile

_GIT_BASH = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
]


def _bash_exe():
    return shutil.which("bash") or next((p for p in _GIT_BASH if shutil.which(p)), "bash")


def bash(command, timeout=30, cwd=None):
    """执行 shell 命令（Git Bash/POSIX），返回 subprocess.CompletedProcess。

    timeout: 硬超时秒数。到时未完成即杀进程 + raise TimeoutExpired。默认 30。

    stdout 实时刷入临时文件（避免 subprocess.PIPE 缓冲区吞输出）；命令完成后
    整体读回作为 CompletedProcess.stdout。stderr 合并到 stdout 保持时序。
    命令的退出码非零是"命令的业务失败"，不是 bash 工具故障——通过 .returncode 判断。
    """
    fd, log_path = tempfile.mkstemp(suffix=".log", prefix="bash-")
    try:
        p = subprocess.Popen(
            [_bash_exe(), "-lc", command],
            stdout=fd, stderr=subprocess.STDOUT, cwd=cwd,
        )
    finally:
        os.close(fd)

    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        # 读已收集的输出附到异常上，模型能看到超时前的进度
        with open(log_path, encoding="utf-8", errors="replace") as f:
            partial = f.read()
        raise subprocess.TimeoutExpired(command, timeout, output=partial)

    with open(log_path, encoding="utf-8", errors="replace") as f:
        output = f.read().rstrip("\r\n")
    return subprocess.CompletedProcess(
        args=command,
        returncode=p.returncode,
        stdout=output,
        stderr="",  # 已合并到 stdout
    )
