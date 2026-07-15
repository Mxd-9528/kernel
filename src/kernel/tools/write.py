"""预置函数 write：写文件（覆盖），自动建父目录，返回写入字节数。

砍掉回读校验、变更 diff、b64/gzip 二进制、空内容报错——
写空是合法操作；要看变更单独调 diff；二进制极罕见时 open(wb) 一行。
"""

import os


def write(file_path, content=""):
    """写文件（覆盖已有），自动创建父目录。返回写入的字节数。

    失败 raise 原生异常（OSError / PermissionError 等）。
    """
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = content.encode("utf-8")
    with open(file_path, "wb") as f:
        f.write(data)
    return len(data)
