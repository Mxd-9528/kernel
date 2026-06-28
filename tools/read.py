"""预置函数 read：读文件，返回带位置锚点的三元组 Result。

支持：文本文件（带行号）、PDF 文件（带页码）、offset/limit 部分读。
失败进 .error 不抛。超长输出由 Result 自动截断（5 万字符，40/20/40 策略）。
"""

from result import Result


def read(file_path, offset=None, limit=None):
    """读文件，返回带行号（文本）或页码（PDF）的内容。

    offset/limit：对文本是行，对 PDF 是页，均从 1 开始计数。
    行号/页码是显示用的，不在文件里。复制给 edit 时只复制原文部分。
    """
    if file_path.lower().endswith(".pdf"):
        return _read_pdf(file_path, offset, limit)
    return _read_text(file_path, offset, limit)


def _read_text(file_path, offset=None, limit=None):
    import os
    if os.path.isdir(file_path):
        e = IsADirectoryError(file_path)
        return Result(f"路径是目录，read 仅支持文件：{file_path}", error=e, file_path=file_path, lines=0)
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

    body = "".join(f"{line_start + i}\t{line}" for i, line in enumerate(chunk))

    n = len(chunk)
    return Result(
        body,
        error=None,
        file_path=file_path,
        lines=n,
        line_start=line_start,
        line_end=line_start + n - 1 if n else line_start - 1,
        bytes=len("".join(chunk).encode("utf-8")),
    )


def _read_pdf(file_path, offset=None, limit=None):
    try:
        import pdfplumber
    except ImportError:
        return Result(
            "读取 PDF 需要 pdfplumber 支持，请执行：pip install pdfplumber",
            error=ImportError("pdfplumber not installed"),
            file_path=file_path,
            pages=0,
        )

    try:
        with pdfplumber.open(file_path) as pdf:
            total = len(pdf.pages)
            start = (offset or 1) - 1
            end = start + limit if limit is not None else total
            pages = pdf.pages[start:end]

            parts = []
            for i, page in enumerate(pages):
                text = page.extract_text() or ""
                if text:
                    parts.append(f"=== 第 {start + 1 + i} 页 ===\n{text}\n\n")

            body = "".join(parts)
            return Result(
                body,
                error=None,
                file_path=file_path,
                pages=total,
                page_start=start + 1,
                page_end=end,
                pages_read=len(pages),
            )
    except Exception as e:
        return Result(f"读取 PDF 失败：{e}", error=e, file_path=file_path, pages=0)
