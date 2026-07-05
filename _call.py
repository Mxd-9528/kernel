import json
import os
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


def _models():
    return json.loads((Path(__file__).parent / "models.json").read_text("utf-8"))


def default_model():
    """默认模型 = models.json 里的第一个（dict 保序）。换默认就把它挪到 json 最前。"""
    return next(iter(_models()))


def call(messages, model=None):
    """把 messages 列表发给模型，返回它的回话文本。无状态：它不记历史，历史是调用方的事。

    messages: [{"role": "user", "content": "..."}, ...]
    model: models.json 里的一个名字，换名字就换模型/接口。None 用默认（json 第一个）。
    key 从环境变量取（名见 models.json 的 key_env），真值存 .env，不入代码/git。
    """
    _load_env()
    cfg = _models()[model or default_model()]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise RuntimeError(f"环境变量 {cfg['key_env']} 未设置——请在 .env 或系统环境变量里配置")
    body = json.dumps({"model": cfg["model"], "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        cfg["url"],
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    msg = resp["choices"][0]["message"]
    reasoning = msg.get("reasoning_content")
    if reasoning:
        # 思维链只在终端显示，不返回、不进 messages、不发给 API
        print("\033[2m" + reasoning + "\033[0m")  # dim 灰显，与正文区分
    return msg["content"]
