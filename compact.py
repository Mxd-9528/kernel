"""上下文压缩：保留 system + 最近 N 轮，把中间旧对话摘要成结构化文本，替换回历史。

轮次数 assistant（模型一轮可能多步工具调用，数 user 会迟迟不触发）；
摘要作 user/assistant 对回插（不塞 system，避免污染系统约束）。
触发用字符数估算（粗略但够；token 精确但要 tokenizer，YAGNI）。
"""

import hashlib
import json
from pathlib import Path

from llm import stream_chat

KEEP_ROUNDS = 6       # 保留最近几轮完整对话（数 assistant）
THRESHOLD = 100_000    # 中间可压部分超过多少字符就触发

_COMPRESS_PROMPT = (Path(__file__).parent / "compact_prompt.md").read_text("utf-8")


def _chars(messages):
    return sum(len(m.get("content", "")) for m in messages)


def split_history(history, keep=KEEP_ROUNDS):
    """拆成 (system, 可压缩中间, 最近keep轮)。轮次数 assistant。不足 keep 轮则中间为空、全保留。"""
    i = 0
    while i < len(history) and history[i]["role"] == "system":
        i += 1
    system, conv = history[:i], history[i:]

    asst = 0
    split = len(conv)
    for j in range(len(conv) - 1, -1, -1):
        if conv[j]["role"] == "assistant":
            asst += 1
            if asst == keep:
                split = j
                break
    if asst < keep:  # 不够 keep 轮，全保留
        return system, [], conv
    # split 落在第 keep 个 assistant 上；往前回退到该轮的 user 起点
    while split > 0 and conv[split - 1]["role"] != "assistant":
        split -= 1
    return system, conv[:split], conv[split:]


def _dedup_tool_outputs(mid):
    """完全相同的环境反馈（内容字节相同）保留最新一份，旧的替换为引用行。"""
    seen = {}  # md5 -> 最新出现的索引
    for i, m in enumerate(mid):
        content = m.get("content", "")
        if m.get("role") != "user" or not content.startswith("[环境反馈]"):
            continue
        h = hashlib.md5(content.encode("utf-8")).hexdigest()
        if h in seen:
            mid[seen[h]] = {"role": "user", "content": f"[环境反馈同下文 #{i}]"}
        seen[h] = i
    return mid


def _compact_mid(mid, model):
    """压缩中间消息，返回桥接消息对 [user, assistant]."""
    mid = _dedup_tool_outputs(list(mid))  # 拷贝，不改原列表
    summary = compress(mid, model)
    return [
        {"role": "user", "content": "（以下是已压缩的旧上下文摘要）"},
        {"role": "assistant", "content": summary},
    ]


def compact(messages, *, keep=KEEP_ROUNDS, threshold=THRESHOLD, model=None):
    """压缩 messages：中间部分字符数超 threshold 才压。未达阈值原样返回。
    压缩时摘要中间部分，作 user/assistant 对回插。model 用于调用压缩 LLM。"""
    system, mid, recent = split_history(messages, keep)
    if not mid or _chars(mid) <= threshold:
        return messages
    return system + _compact_mid(mid, model) + recent


def compress(messages, model):
    """把待压消息拼成压缩请求并调用模型，返回摘要文本。提出来独立可测 COMPRESS_PROMPT 拼装。"""
    req = [
        {"role": "system", "content": _COMPRESS_PROMPT},
        {"role": "user", "content": json.dumps(messages, ensure_ascii=False)},
    ]
    return "".join(token for kind, token in stream_chat(req, model) if kind == "content")


# ── 观察者 ──────────────────────────────────────────────────

from observer import BaseObserver

class _CompactObserver(BaseObserver):
    def before_send(self, messages, model):
        messages[:] = compact(messages, model=model)


observer = _CompactObserver()
