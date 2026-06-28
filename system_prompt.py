"""组装系统提示词：prompt.txt + 预置函数 + 技能 + MCP 服务器 + 用户自定义追加。

所有系统提示相关的逻辑都集中在这里，避免 agent.py 膨胀。
加新的提示源只改这个文件，其他地方不动。
"""

from pathlib import Path


def build():
    """组装完整的系统提示词。

    组装顺序（优先级从低到高，后面的可以覆盖前面的语境）：
    1. prompt.txt - 核心基础提示
    2. 预置函数清单（manifest）
    3. 技能清单（skills）
    4. MCP 服务器清单
    5. system_append.txt - 用户自定义追加（最高优先级）
    """
    from manifest import list_tools
    from skills import list_skills

    base = (Path(__file__).parent / "prompt.txt").read_text("utf-8")
    out = base + "\n\n# 预置函数（已注入命名空间，直接调用，无需 import）\n\n" + list_tools()

    # 技能清单
    sk = list_skills()
    if sk:
        out += "\n\n# 技能\n\n" + sk

    # 用户自定义系统提示追加：有文件就自动追加，没有就跳过
    append_path = Path(__file__).parent / "system_append.txt"
    if append_path.exists():
        out += "\n\n" + append_path.read_text("utf-8")

    return out
