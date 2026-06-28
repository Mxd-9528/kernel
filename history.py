"""对话历史持久化：单会话，存项目目录的 history.json，启动自动接续。

存盘前清掉 reasoning_content（思维链不进历史、体积大、发回 API 也没用）。
损坏/缺失当作无历史，不崩——历史是便利，不该让坏文件挡住启动。
"""

import json
from pathlib import Path

_PATH = Path(__file__).parent / "history.json"


def save(messages, path=_PATH):
    """存对话历史。清掉每条的 reasoning_content（不改原列表）。"""
    clean = [{k: v for k, v in m.items() if k != "reasoning_content"} for m in messages]
    Path(path).write_text(json.dumps(clean, ensure_ascii=False, indent=2), "utf-8")


def load(path=_PATH):
    """读对话历史。无文件或损坏返回 None（当作无历史）。"""
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
