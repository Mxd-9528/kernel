"""LLM 调用工具：读配置、发请求、取回复。"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from collections.abc import Generator
from pathlib import Path

# 用 __file__ 推导项目根，避免 cwd() 在子目录运行或 os.chdir() 后飘移
_ROOT = Path(__file__).resolve().parent.parent.parent

_ENV_LOADED = False


def _load_env() -> None:
    """把 .env 的 K=V 读进环境变量（已存在的不覆盖）。无 .env 则跳过。幂等。"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def list_models() -> dict[str, dict]:
    data = json.loads((_ROOT / "models.json").read_text("utf-8"))
    return {k: v for k, v in data.items() if k != "default"}


def default_model() -> str:
    data = json.loads((_ROOT / "models.json").read_text("utf-8"))
    return data["default"]


def stream_chat(messages: list[dict], model: str | None = None) -> Generator[tuple[str, str], None, None]:
    """向 LLM 发流式请求，逐 token yield。"""
    _load_env()
    cfg = list_models()[model or default_model()]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise RuntimeError(f"环境变量 {cfg['key_env']} 未设置——请在 .env 或系统环境变量里配置")

    body = json.dumps({
        "model": cfg["model"],
        "messages": messages,
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        cfg["url"],
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e

    # 完整性追踪：区分"正常读到 [DONE]"与"迭代器静默结束"
    finished_cleanly = False
    last_finish_reason: str | None = None

    for line_bytes in resp:
        line = line_bytes.decode("utf-8").strip()
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            finished_cleanly = True
            break
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        choices = chunk.get("choices")
        if not choices:
            continue
        # OpenAI 兼容协议：finish_reason 明确告知终止原因
        fr = choices[0].get("finish_reason")
        if fr:
            last_finish_reason = fr
        delta = choices[0].get("delta", {})
        reasoning = delta.get("reasoning_content")
        if reasoning:
            yield "thinking", reasoning
        content = delta.get("content", "")
        if content:
            yield "content", content

    # 终止信号：调用者据此决定是否追加告警
    #   "stop"           模型自然结束
    #   "length"         达到 max_tokens
    #   "content_filter" 内容被过滤
    #   "tool_calls"     工具调用（本项目未启用）
    #   "incomplete"     流被切断，未收到 [DONE]（网关超时 / 连接中断）
    yield "finish", last_finish_reason if finished_cleanly else "incomplete"


