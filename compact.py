"""上下文压缩层接口。实现见 _compact.py。

should_compact(history, keep=6, threshold=50_000) -> bool
    判断 history 是否需要压缩。history 拆成 (system, 中间可压部分, 最近 keep 轮)；
    中间部分字符数超 threshold 即 True。keep 按 assistant 消息计数；字符数为粗估。

compact(history, keep=6, model=None) -> list
    压缩 history，返回可无缝续用的更短消息序列：
    [system 原样] + [摘要 user/assistant 对] + [最近 keep 轮原样]。
    不足 keep 轮时原样返回 history。
    model=None 时取 call 层默认模型。
    Raises: 透传 call 接口的异常（参见 call）。
"""
from _compact import should_compact, compact
