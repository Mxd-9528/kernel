"""三元组反馈载体：Body + .error + .facts。

代码块（含预置函数）的反馈接口。Body 是语义主值，可直接当 str/list/dict 用；
.error 是代码块自身的失败通道（成功 None，失败承载原生异常对象）；
.facts 是非主体原生事实记录。

对齐设计：error= 强制必填，逼调用方显式表态成功/失败，杜绝忘设 error 的静默成功。
facts 既整体挂在 .facts，又每个 key setattr 成属性，两种取法都行。
"""

_ERROR_REQUIRED = "error= 必填；成功传 None"


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
    parts = [body_text]
    if obj.error is not None:
        parts.append(f"error={obj.error!r}")
    facts = "  ".join(f"{k}={v!r}" for k, v in obj.facts.items())
    if facts:
        parts.append(facts)
    return "\n".join(parts)


class Result(str):
    """Body 是字符串的三元组结果。"""

    def __new__(cls, body="", **facts):
        return _attach(str.__new__(cls, body), facts)

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