"""预置函数 read：读文件，返回带行号的三元组 Result。

支持：cat -n 行号（模型靠行号定位）、offset/limit 部分读、错误分类
（目录/权限/编码/不存在），失败进 .error 不抛。截断用 lazy 版（超行数截尾+提示），
不搬 40/20/40——文件从头读，截尾足够；等大输出分流再上完整截断。
"""

from result import Result

_MAX_LINES = 2000  # ponytail: 超此行数截尾


def read(file_path, offset=None, limit=None):
    """读文件，返回带行号（`数字+tab`）的文本。offset（起始行，从1计）、limit（最大行数）可选，支持部分读。

    行号是显示用的，不在文件里。把内容复制给 edit 的 old_string 时，只复制行号后的原文。
    """
    import os
    if os.path.isdir(file_path):  # 跨平台：Windows 打开目录抛 PermissionError 而非 IsADirectoryError
        e = IsADirectoryError(file_path)
        return Result(f"路径是目录，read 仅支持文本文件：{file_path}", error=e, file_path=file_path, lines=0)
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError as e:
        return Result(f"文件不存在：{file_path}", error=e, file_path=file_path, lines=0)
    except PermissionError as e:
        return Result(f"无权读取 {file_path}：{e}", error=e, file_path=file_path, lines=0)
    except UnicodeDecodeError as e:
        return Result(f"无法按 UTF-8 解码 {file_path}：{e.reason}", error=e, file_path=file_path, lines=0)

    start = (offset or 1) - 1
    end = start + limit if limit is not None else len(lines)
    chunk = lines[start:end]
    line_start = start + 1

    truncated = len(chunk) > _MAX_LINES
    shown = chunk[:_MAX_LINES]
    body = "".join(f"{line_start + i}\t{line}" for i, line in enumerate(shown))
    if truncated:
        body += f"\n... [已截断，共 {len(chunk)} 行，仅显示前 {_MAX_LINES} 行，用 offset/limit 读其余]"

    n = len(chunk)
    return Result(
        body,
        error=None,
        file_path=file_path,
        lines=n,
        line_start=line_start,
        line_end=line_start + n - 1 if n else line_start - 1,
        bytes=len("".join(chunk).encode("utf-8")),
        truncated=truncated,
    )
