"""预置函数 edit：精确替换文件文本，返回 file:line 和变更 diff。

精确匹配 + 唯一性检查（多处匹配需 replace_all，防误改）、
花引号归一化容错（模型常把直引号输成花引号）、返回行号定位、内置变更 diff。
diff 合并进 edit——改完顺手给变更，是 edit 结果的一部分（.facts['diff']），不单列工具。
砍掉行尾空格容错、删除连带换行处理——边界复杂度高、收益低。
"""

import difflib

from result import Result

_CURLY = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "„": '"'})


def _diff(old, new, max_lines=30):
    lines = [
        ln.rstrip()
        for ln in difflib.unified_diff(old.splitlines(), new.splitlines(), n=0, lineterm="")
        if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
    ]
    out = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        out += f"\n... 还有 {len(lines) - max_lines} 行变更"
    return out


def edit(file_path, old_string, new_string, replace_all=False):
    """精确替换文件中的文本，old_string 须唯一匹配（多处需 replace_all=True）。返回 file:line，facts 带变更 diff。

    old_string 用文件的纯文本内容，不要带 read 显示的行号前缀（`数字+tab`）——edit 在磁盘原文上匹配，行号是 read 加的。
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError as e:
        return Result("", error=e, file_path=file_path)

    # 精确匹配；不中则花引号归一化后再试（模型常把 " 输成 “”）
    target = old_string
    if content.count(target) == 0:
        norm = old_string.translate(_CURLY)
        if norm != old_string and content.count(norm) > 0:
            target = norm

    count = content.count(target)
    if count == 0:
        return Result("", error=ValueError("old_string 未匹配文件内容"), file_path=file_path, count=0)
    if count > 1 and not replace_all:
        return Result("", error=ValueError(f"old_string 匹配了 {count} 处，需 replace_all=True"),
                      file_path=file_path, count=count)

    new_content = content.replace(target, new_string, -1 if replace_all else 1)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    line = content[: content.index(target)].count("\n") + 1
    return Result(f"{file_path}:{line}", error=None, file_path=file_path,
                  line=line, replace_all=replace_all, diff=_diff(content, new_content))
