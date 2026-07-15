"""预置函数 glob：按模式递归查找文件，返回路径列表。

自动递归（没写 ** 也补 **/）、路径归一化（\\→/、折叠 ./）、去重。
按修改时间倒序（最近改的排前，模型多半想要最新的）。
排除规则与 grep 共享（单一事实源），不命中 __pycache__/.git/*.pyc/history.json 等噪声。
无匹配返回空列表（不 raise）。
"""

import fnmatch
import glob as _glob
import os

from .exclude import _EXCLUDE, _EXCLUDE_FILES  # 单一事实源


def _norm(path):
    p = os.path.normpath(path).replace("\\", "/")
    return p[2:] if p.startswith("./") else p


def _is_noise(path):
    parts = path.replace("\\", "/").rstrip("/").split("/")
    if any(seg in _EXCLUDE for seg in parts):
        return True
    return any(fnmatch.fnmatch(parts[-1], pat) for pat in _EXCLUDE_FILES)


def glob(pattern, path="."):
    """递归查找匹配 pattern 的文件，按修改时间倒序返回路径列表。path 指定搜索根目录。"""
    full = os.path.join(path, pattern if "**" in pattern else os.path.join("**", pattern))
    hits = [p for p in dict.fromkeys(_glob.glob(full, recursive=True)) if not _is_noise(p)]
    hits.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return [_norm(p) for p in hits]
