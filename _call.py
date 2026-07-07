import json
import os
import time
import urllib.request
from pathlib import Path

_ENV_LOADED = False


def _load_env():
    """把 .env 的 K=V 读进环境变量（已存在的不覆盖）。无 .env 则跳过。
    幂等：只在第一次调用时真正加载，后续调用直接返回。
    """
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


def list_models():
    return json.loads((Path(__file__).parent / "models.json").read_text("utf-8"))


def default_model():
    """默认模型 = models.json 里的第一个（dict 保序）。换默认就把它挪到 json 最前。"""
    return next(iter(list_models()))


def _prepare_request(messages, model=None, stream=False):
    """共用：组装请求并发送，返回 HTTP 响应对象。"""
    _load_env()
    cfg = list_models()[model or default_model()]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise RuntimeError(f"环境变量 {cfg['key_env']} 未设置——请在 .env 或系统环境变量里配置")
    body = {"model": cfg["model"], "messages": messages}
    if stream:
        body["stream"] = True
    req = urllib.request.Request(
        cfg["url"],
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req)


def call(messages, model=None):
    """把 messages 列表发给模型，返回它的回话文本。无状态：它不记历史，历史是调用方的事。

    messages: [{"role": "user", "content": "..."}, ...]
    model: models.json 里的一个名字，换名字就换模型/接口。None 用默认（json 第一个）。
    key 从环境变量取（名见 models.json 的 key_env），真值存 .env，不入代码/git。
    """
    resp = json.loads(_prepare_request(messages, model).read())
    msg = resp["choices"][0]["message"]
    reasoning = msg.get("reasoning_content")
    if reasoning:
        # 思维链只在终端显示，不返回、不进 messages、不发给 API
        print("\033[2m" + reasoning + "\033[0m")  # dim 灰显，与正文区分
    return msg["content"]


def call_streaming(messages, model=None):
    """流式版 call()：逐 token 用 Rich Live 增量渲染 Markdown。

    用法和 call() 完全相同，只是多了实时逐字渲染的副作用。
    返回完整文本，失败时 fallback 到原始 call()。
    思维链（reasoning_content）静默跳过，不占终端。
    """
    from rich.live import Live
    from rich.markdown import Markdown

    resp = _prepare_request(messages, model, stream=True)

    collected = ""
    live = Live(
        Markdown(""),
        refresh_per_second=60,
        screen=False,
        vertical_overflow="visible",
    )
    live.start()

    try:
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

            # 思维链：静默跳过，不占终端
            if delta.get("reasoning_content"):
                continue

            content = delta.get("content", "")
            if content:
                for ch in content:
                    collected += ch
                    live.update(Markdown(collected))
                    time.sleep(0.008)
    except Exception:
        live.stop()
        live.console.print("\n[流式失败，fallback 到普通调用]")
        result = call(messages, model)
        live.console.print(Markdown(result))
        return result
    finally:
        live.stop()

    return collected
