"""自动扫描 tools/ 生成预置函数清单——单一事实源，免漂移。

约定：tools/x.py 里跟文件同名的函数 x，就是一个预置函数。
描述全靠 inspect 自省（签名 + docstring），不手写 schema——改函数即改描述。
这是 kernel 范式（写代码→看结果）该有的做法，不是 function-calling 的 JSON schema。
"""

import importlib
import inspect
import pkgutil

import tools


def presets():
    """扫 tools/，返回 [(name, func), ...]：每个模块里与模块同名的函数。"""
    out = []
    for info in pkgutil.iter_modules(tools.__path__):
        mod = importlib.import_module(f"tools.{info.name}")
        func = getattr(mod, info.name, None)
        if inspect.isfunction(func):
            out.append((info.name, func))
    return sorted(out)


def list_tools():
    """拼成 prompt 用的预置函数清单：name(签名) + 完整 docstring（含多行陷阱说明）。"""
    lines = []
    for name, func in presets():
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""
        indented = "\n".join("  " + ln for ln in doc.splitlines())
        lines.append(f"- {name}{sig}\n{indented}")
    return "\n".join(lines)
