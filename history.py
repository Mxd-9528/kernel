"""对话历史持久化：单会话，存项目目录的 history.json，启动自动接续。

损坏/缺失当作无历史，不崩——历史是便利，不该让坏文件挡住启动。
"""

import json
import os
from pathlib import Path

from agent import EVENT_SAVE

_PATH = Path(os.environ.get("HISTORY_PATH", Path(__file__).parent / "history.json"))


def save(messages, path=_PATH):
    """存对话历史。"""
    Path(path).write_text(json.dumps(messages, ensure_ascii=False, indent=2), "utf-8")


def load(path=_PATH):
    """读对话历史。无文件或损坏返回 None（当作无历史）。"""
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def reset_history():
    """清空持久化文件，返回包含系统提示的初始消息列表。"""
    save([])
    from system import build_system
    return [{"role": "system", "content": build_system()}]


def on_save(messages):
    """事件驱动存盘。"""
    save(messages)
