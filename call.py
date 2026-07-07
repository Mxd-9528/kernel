"""LLM 调用层接口。实现见 _call.py。

call(messages, model=None) -> str
    向 LLM 发送 messages 返回回复文本。无状态。
    messages: [{"role": "user"|"assistant"|"system", "content": str}, ...]
    model=None 时取 default_model()。
    Raises: RuntimeError (cfg["key_env"] 未设置) / HTTPError / URLError / json.JSONDecodeError。
    Side effects: 首次调用把 .env 加载进 os.environ（幂等）；
                  reasoning_content 以 dim 灰打印到 stdout，不进返回值也不进 messages。

call_streaming(messages, model=None) -> str
    流式版 call()：逐 token 用 Rich Live 增量渲染 Markdown。
    用法和 call() 完全相同，接口不变，失败时自动 fallback 到 call()。

default_model() -> str
    返回 models.json 首个键名。

list_models() -> dict
    返回 models.json 全表；供 /model 命令枚举。
"""
from _call import call, call_streaming, default_model, list_models
