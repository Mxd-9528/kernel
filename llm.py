"""LLM 调用工具：读配置、发请求、取回复。"""
import json
import os
from pathlib import Path

_ENV_LOADED = False


def _load_env():
    """把 .env 的 K=V 读进环境变量（已存在的不覆盖）。无 .env 则跳过。幂等。"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env = Path(__file__).parent / ".env"
    if not env.exists():
        return
    for line in env.read_text("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _list_models():
    return json.loads((Path(__file__).parent / "models.json").read_text("utf-8"))


def _default_model():
    return next(iter(_list_models()))


def call(messages, model=None):
    """非流式调 LLM，无终端显示。流式失败时做 fallback。"""
    _load_env()
    cfg = _list_models()[model or _default_model()]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise RuntimeError(f"环境变量 {cfg['key_env']} 未设置——请在 .env 或系统环境变量里配置")
    body = json.dumps({"model": cfg["model"], "messages": messages}).encode("utf-8")
    import urllib.request
    req = urllib.request.Request(
        cfg["url"],
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["choices"][0]["message"]["content"]


def stream_chat(messages, model=None):
    """向 LLM 发流式请求，逐 token yield。"""
    _load_env()
    cfg = _list_models()[model or _default_model()]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise RuntimeError(f"环境变量 {cfg['key_env']} 未设置——请在 .env 或系统环境变量里配置")

    body = json.dumps({
        "model": cfg["model"],
        "messages": messages,
        "stream": True,
    }).encode("utf-8")

    import urllib.request
    req = urllib.request.Request(
        cfg["url"],
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)

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
        if delta.get("reasoning_content"):
            continue
        content = delta.get("content", "")
        if content:
            yield content


# ── 事件注册：收到 send 事件 → 发请求 → 追1 ──────────────────────────

from agent import on, stop
from display import render_stream


@on("send")
def _on_send(state):
    """发请求，取回复，追加到 state.messages。"""
    if stop.is_set():
        return
    model = getattr(state, "model", None)

    try:
        reply = render_stream(stream_chat(state.messages, model))
    except Exception:
        reply = call(state.messages, model)

    state.messages.append({"role": "assistant", "content": reply})
