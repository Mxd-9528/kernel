"""三元组反馈载体：Body + .error + .facts。

代码块（含预置函数）的反馈接口。Body 是语义主值，可直接当 str/list/dict 用；
.error 是代码块自身的失败通道（成功 None，失败承载原生异常对象）；
.facts 是非主体原生事实记录。

对齐设计：error= 强制必填，逼调用方显式表态成功/失败，杜绝忘设 error 的静默成功。
facts 既整体挂在 .facts，又每个 key setattr 成属性，两种取法都行。

自动截断：所有 Result body 超过 2 万字符时自动按 40/20/40 策略截断，防止爆 token。
"""

_ERROR_REQUIRED = "error= 必填；成功传 None"
_MAX_BODY = 20000  # 2 万字符 ≈ 5000 token，安全距离（约 1300 行普通代码）


def _truncate_402040(s: str, limit: int = _MAX_BODY) -> tuple:
    """40/20/40 三段截断：头/中/尾各保留 40%/20%/40%，返回 (截断后文本, 是否截断)。"""
    if len(s) <= limit:
        return s, False

    head_n = int(limit * 0.4)
    middle_n = int(limit * 0.2)
    tail_n = limit - head_n - middle_n

    head = s[:head_n]
    middle_start = (len(s) - middle_n) // 2
    middle = s[middle_start:middle_start + middle_n]
    tail = s[-tail_n:]

    truncated = (
        f"{head}\n"
        f"\n[... 截断 {len(s) - limit:,} 字符，保留头/中/尾各 40%/20%/40% ...]\n\n"
        f"{middle}\n"
        f"\n[... 截断继续 ...]\n\n"
        f"{tail}"
    )
    return truncated, True


def _attach(obj, facts):
    if "error" not in facts:
        raise TypeError(_ERROR_REQUIRED)
    obj.error = facts.pop("error")
    obj.facts = facts
    for k, v in facts.items():
        setattr(obj, k, v)
    return obj


def _repr(obj, body_text):
    # 原样转达三元组：Body + error（非 None 才显示）+ facts 整字典倒出，不挑字段。
    # run() 对表达式值调 repr()，所以这里就是三元组到达模型的坍缩点。
    # ponytail: 统一在此截断——所有 Result 类型的 repr 都经过这里，不用每个类单独改。
    body_text, truncated = _truncate_402040(body_text)
    parts = [body_text]
    if obj.error is not None:
        parts.append(f"error={obj.error!r}")
    if truncated:
        parts.append(f"truncated=True")
    facts = "  ".join(f"{k}={v!r}" for k, v in obj.facts.items())
    if facts:
        parts.append(facts)
    return "\n".join(parts)


class Result(str):
    """Body 是字符串的三元组结果。所有类型统一在 _repr 处截断。"""

    def __new__(cls, body="", **facts):
        obj = str.__new__(cls, str(body))
        _attach(obj, facts)
        return obj

    def __repr__(self):
        return _repr(self, str(self))


class ListResult(list):
    """Body 是列表的三元组结果。"""

    def __init__(self, items=(), **facts):
        super().__init__(items)
        _attach(self, facts)

    def __repr__(self):
        return _repr(self, list.__repr__(self))


class DictResult(dict):
    """Body 是字典的三元组结果。"""

    def __init__(self, mapping=None, **facts):
        super().__init__(mapping or {})
        _attach(self, facts)

    def __repr__(self):
        return _repr(self, dict.__repr__(self))