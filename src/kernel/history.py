"""对话历史持久化：单会话，存项目目录的 history.json，启动自动接续。

损坏/缺失当作无历史，不崩——历史是便利，不该让坏文件挡住启动。
"""

import json
import os
from pathlib import Path


# 用 __file__ 推导项目根，避免 cwd() 在子目录运行或 os.chdir() 后飘移
_ROOT = Path(__file__).resolve().parent.parent.parent
_PATH = Path(os.environ.get("HISTORY_PATH", _ROOT / "history.json"))


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
    from .system import build_system
    return [{"role": "system", "content": build_system()}]


# ── 观察者 ──────────────────────────────────────────────────

from .observer import BaseObserver

class _HistoryObserver(BaseObserver):
    def save(self, messages):
        save(messages)


observer = _HistoryObserver()
