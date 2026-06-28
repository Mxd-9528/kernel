import re

# 外层 <!EXEC>...</EXEC> 是真边界（代码里不会出现）；内层 ``` 顺着模型天性。
# re.DOTALL 让 . 匹配换行，否则多行代码会被吞掉只剩第一行。
pattern = r"<!EXEC>\s*```\s*\w*\n?(.*?)```\s*</EXEC>"


def extract(text):
    """从模型回话里抠出所有 <!EXEC> 代码块，返回代码字符串列表。"""
    return [m.strip() for m in re.findall(pattern, text, re.DOTALL)]