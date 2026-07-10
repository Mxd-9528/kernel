"""预置函数 read：读文件，返回带行号（文本）或页码（PDF）的字符串。

支持：文本文件（带行号）、PDF 文件（带页码）、offset/limit 部分读。
失败通过 raise 传递原生异常（FileNotFoundError / IsADirectoryError / UnicodeDecodeError）。
"""

import os


def read(file_path, offset=None, limit=None):
    """读文件，返回带行号（文本）或页码（PDF）的字符串。

    offset/limit：对文本是行，对 PDF 是页，均从 1 开始计数。
    行号/页码是显示用的，不在文件里。复制给 edit 时只复制原文部分。

    prompt.txt 已注入 system prompt，不必 read 它。
    """
    if file_path.lower().endswith(".pdf"):
        return _read_pdf(file_path, offset, limit)
    return _read_text(file_path, offset, limit)


def _read_text(file_path, offset=None, limit=None):
    if os.path.isdir(file_path):
        raise IsADirectoryError(f"路径是目录，read 仅支持文件：{file_path}")

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    start = (offset if offset is not None else 1) - 1
    end = start + limit if limit is not None else len(lines)
    chunk = lines[start:end]
    line_start = start + 1

    return "".join(f"{line_start + i}\t{line}" for i, line in enumerate(chunk))


def _read_pdf(file_path, offset=None, limit=None):
    try:
        import pdfplumber
    except ImportError:
        import subprocess
        import sys
        print("[正在自动安装 pdfplumber，首次使用请稍候...]")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
        import pdfplumber
        print("[pdfplumber 安装完成]")

    with pdfplumber.open(file_path) as pdf:
        total = len(pdf.pages)
        start = (offset if offset is not None else 1) - 1
        end = start + limit if limit is not None else total
        pages = pdf.pages[start:end]

        parts = []
        for i, page in enumerate(pages):
            text = page.extract_text() or ""
            if text:
                parts.append(f"=== 第 {start + 1 + i} 页 ===\n{text}\n\n")

        return "".join(parts)
