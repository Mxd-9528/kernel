"""预置函数 grep：递归正则搜索文件内容，三种 output_mode。

支持：三种 output_mode（content/files_with_matches/count）按需选粒度、
默认排除噪声目录、glob 过滤、大小写开关。用 re 不用 ripgrep（kernel 全标准库，不引外部二进制）。
失败通过 raise 传递（re.error / ValueError）。
"""

import fnmatch
import os
import re

from .exclude import _EXCLUDE, _EXCLUDE_FILES

_MODES = {"content", "files_with_matches", "count"}


def _norm(p):
    return os.path.normpath(p).replace("\\", "/")


def grep(pattern, path=".", glob=None, output_mode="content", case_insensitive=False):
    """递归正则搜索文件内容。output_mode: content（默认，list[dict] 含 file+lines）/ files_with_matches（list[str] 路径）/ count（dict[str,int] 每文件匹配数）。glob 按文件名过滤，case_insensitive 大小写不敏感。"""
    if output_mode not in _MODES:
        raise ValueError(f"无效 output_mode：{output_mode}")

    rx = re.compile(pattern, re.IGNORECASE if case_insensitive else 0)

    content, counts, files = [], {}, set()

    def scan(fp):
        fp = _norm(fp)
        try:
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if not rx.search(line):
                        continue
                    files.add(fp)
                    if output_mode == "content":
                        if not content or content[-1]["file"] != fp:
                            content.append({"file": fp, "lines": []})
                        content[-1]["lines"].append({"line": i, "text": line.rstrip()})
                    elif output_mode == "count":
                        counts[fp] = counts.get(fp, 0) + 1
        except OSError:
            pass  # 读不了就跳过，不记录每文件错误——模型不需要权限清单

    if os.path.isfile(path):
        scan(path)
    else:
        for root, dirs, names in os.walk(path):
            dirs[:] = [x for x in dirs if x not in _EXCLUDE]
            for f in names:
                if any(fnmatch.fnmatch(f, pat) for pat in _EXCLUDE_FILES):
                    continue
                if glob and not fnmatch.fnmatch(f, glob):
                    continue
                scan(os.path.join(root, f))

    if output_mode == "count":
        return counts
    if output_mode == "files_with_matches":
        return sorted(files)
    return content
