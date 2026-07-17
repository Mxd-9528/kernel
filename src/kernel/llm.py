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

    for line_bytes in resp:
        line = line_bytes.decode("utf-8").strip()
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        choices = chunk.get("choices")
        if not choices:
            continue
        delta = choices[0].get("delta", {})
        reasoning = delta.get("reasoning_content")
        if reasoning:
            yield "thinking", reasoning
        content = delta.get("content", "")
        if content:
            yield "content", content


