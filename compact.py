"""上下文压缩层接口。实现见 _compact.py。

compact(history, keep=6, threshold=50_000, model=None) -> list
    压缩 history，返回可无缝续用的更短消息序列。未达阈值原样返回。
    结构：[system 原样] + [摘要 user/assistant 对] + [最近 keep 轮原样]。
    keep 按 assistant 消息计数；threshold 是中间可压部分字符数阈值（粗估）。
    model=None 时取 call 层默认模型。
    Raises: 透传 call 接口的异常（参见 call）。
"""
from _compact import compact
