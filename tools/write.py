"""预置函数 write：写文件（覆盖），自动建父目录，返回三元组。

砍掉回读校验、变更 diff、b64/gzip 二进制、空内容报错——
写空是合法操作；要看变更单独调 diff；二进制极罕见时 open(wb) 一行。
不做「覆盖前必须先 read」的硬检查——kernel 无读状态跟踪，靠 prompt 约定（先 read 再 write）。
"""

import os

from result import Result


def write(file_path, content=""):
    """写文件（覆盖已有），自动创建父目录。返回文件路径，facts 带 bytes 字节数。"""
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return Result(file_path, error=None, file_path=file_path, bytes=len(content.encode("utf-8")))
