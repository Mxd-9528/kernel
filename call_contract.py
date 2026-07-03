"""call 合同 —— 沉淀线，上游只读这份，不下潜 call.py。

def call(messages, model=None) -> str:
    把 messages 发给 LLM，返回回复文本。无状态。

    messages: [{"role": "user"|"assistant"|"system", "content": str}, ...]
    model:    models.json 里的键名；None → default_model()
    返回:     str，模型回复正文

    失败:
      RuntimeError: 环境变量 (cfg["key_env"]) 未设置
      其他异常透传: urllib HTTPError / URLError / json 解析错误

    副作用:
      首次调用读 .env → os.environ（幂等，不覆盖已存在的 key）
      响应含 reasoning_content 时 dim 灰打印到 stdout；不进返回值、不进 messages

def default_model() -> str:
    models.json 首个键名。换默认就把它挪到 json 最前。
"""
from call import call, default_model
