"""预置函数 grep：递归正则搜索文件内容，三种 output_mode。

支持：三种 output_mode（content/files_with_matches/count）按需选粒度、
默认排除噪声目录、glob 过滤、大小写开关。
砍掉「部分扫描错误状态机」——读不了的文件 errors='ignore' 跳过即可，
模型不需要逐个文件的权限错误清单。用 re 不用 ripgrep（kernel 全标准库，不引外部二进制）。
"""

import fnmatch
import os
import re

from result import ListResult, DictResult
from tools.exclude import _EXCLUDE, _EXCLUDE_FILES  # 单一事实源

_MODES = {"content", "files_with_matches", "count"}


def _norm(p):
    return os.path.normpath(p).replace("\\", "/")


def grep(pattern, path=".", glob=None, output_mode="content", case_insensitive=False):
    """递归正则搜索文件内容。output_mode: content（默认，含文件+行号+文本）/ files_with_matches（路径列表）/ count（每文件匹配数）。glob 按文件名过滤，case_insensitive 大小写不敏感。"""
    # files_matched/lines_matched 给默认 0，保证错误分支也有这俩字段——facts schema 稳定
    facts = dict(pattern=pattern, path=path, output_mode=output_mode, files_matched=0, lines_matched=0)
    empty = DictResult if output_mode == "count" else ListResult
    if output_mode not in _MODES:
        return empty(error=ValueError(f"无效 output_mode：{output_mode}"), **facts)
    try:
        rx = re.compile(pattern, re.IGNORECASE if case_insensitive else 0)
    except re.error as e:
        return empty(error=e, **facts)

    content, counts, files, lines_matched = [], {}, set(), 0

    def scan(fp):
        nonlocal lines_matched
        fp = _norm(fp)
        try:
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if not rx.search(line):
                        continue
                    lines_matched += 1
                    files.add(fp)
                    if output_mode == "content":
                        if not content or content[-1]["file"] != fp:
                            content.append({"file": fp, "lines": []})
                        content[-1]["lines"].append({"line": i, "text": line.rstrip()})
                    elif output_mode == "count":
                        counts[fp] = counts.get(fp, 0) + 1
        except OSError:
            pass  # ponytail: 读不了就跳过，不记录每文件错误——模型不需要权限清单

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

    facts.update(files_matched=len(files), lines_matched=lines_matched)
    if output_mode == "count":
        return DictResult(counts, error=None, **facts)
    if output_mode == "files_with_matches":
        return ListResult(sorted(files), error=None, **facts)
    return ListResult(content, error=None, **facts)
