"""预置函数 survey：测绘 Python 项目架构，缓存进内核内存，按需查询全景/细节/波及面。

测绘一次后自动缓存（不进 LLM 上下文），后续 overview/detail/impact 都查缓存，
避免将整张图谱塞给模型。作为 read 的前置工具——先 survey 了解概况，再 read 读具体文件。

用法：
    survey("项目目录")                  # 第一次测绘并缓存
    survey(mode="overview")             # 全景：每模块一行
    survey(mode="detail", target="x")   # 单模块细节
    survey(mode="impact", target="x")   # 改它波及谁
"""

import ast
import inspect
import os
import sys

from result import ListResult, Result

_cache = {}

_EXCLUDE = frozenset({
    "__pycache__", ".git", ".ruff_cache", ".claude", ".venv", "venv",
    "node_modules", ".idea", "skills",
})


def _summary(doc):
    return doc.strip().splitlines()[0].strip() if doc else ""


def _modname(path, base):
    rel = os.path.relpath(path, base)[:-3]
    if rel.endswith(os.sep + "__init__"):
        rel = rel[:-len(os.sep + "__init__")]
    return rel.replace(os.sep, ".")


def _scan(path):
    path = os.path.abspath(path)
    files = []
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d not in _EXCLUDE]
        for f in names:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))

    tops = {_modname(f, path).split(".")[0] for f in files}
    graph = {}

    for fp in files:
        mod = _modname(fp, path)
        try:
            with open(fp, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            graph[mod] = {"file": os.path.relpath(fp, path), "error": str(e)}
            continue

        funcs, classes, imps = [], [], []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                funcs.append({"name": node.name,
                              "args": [a.arg for a in node.args.args],
                              "lineno": node.lineno,
                              "summary": _summary(ast.get_docstring(node))})
            elif isinstance(node, ast.ClassDef):
                bases = [b.id if isinstance(b, ast.Name) else b.attr
                         for b in node.bases if isinstance(b, (ast.Name, ast.Attribute))]
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({"name": node.name, "bases": bases,
                                "lineno": node.lineno, "methods": methods,
                                "summary": _summary(ast.get_docstring(node))})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                m = getattr(node, "module", "") or ""
                for n in node.names:
                    imps.append({"module": m, "name": n.name})

        deps = sorted({i["module"].split(".")[0] for i in imps
                       if i["module"].split(".")[0] in tops} - {mod.split(".")[0]})

        # 活对象补全：已加载的模块直接 inspect 拿真实签名和 MRO
        if mod in sys.modules:
            m = sys.modules[mod]
            for f in funcs:
                obj = getattr(m, f["name"], None)
                if obj and callable(obj):
                    try:
                        f["signature"] = str(inspect.signature(obj))
                    except Exception:
                        pass
            for c in classes:
                obj = getattr(m, c["name"], None)
                if obj and isinstance(obj, type):
                    c["mro"] = [x.__name__ for x in obj.__mro__]

        graph[mod] = {"file": os.path.relpath(fp, path),
                      "summary": _summary(ast.get_docstring(tree)),
                      "functions": funcs, "classes": classes, "deps": deps}
    return graph


def survey(path=".", mode="scan", target=None):
    """测绘/查询 Python 项目架构。第一次自动测绘并缓存，后续查缓存不进 LLM 上下文。

    survey("项目目录")               — 测绘
    survey(mode="overview")          — 全景：每模块一行（函数/类数、依赖、摘要）
    survey(mode="detail", target=X)  — 单模块：签名、MRO、方法
    survey(mode="impact", target=X)  — 反向依赖：改 X 会波及谁
    """
    global _cache
    if mode == "scan" or not _cache:
        _cache = _scan(path)

    if mode == "scan":
        return Result(f"测绘完成，共 {len(_cache)} 个模块", error=None)
    if mode == "overview":
        lines = []
        for m in sorted(_cache):
            i = _cache[m]
            if "error" in i:
                lines.append(f"{m}  [解析失败]")
                continue
            dep = f" →{','.join(i['deps'])}" if i["deps"] else ""
            lines.append(f"{m} ({len(i['functions'])}f/{len(i['classes'])}c)"
                         f"{dep}  {i.get('summary','')}")
        return Result("\n".join(lines), error=None)
    if mode == "detail":
        if not target:
            return Result("", error="需要 target= 指定模块名")
        i = _cache.get(target)
        if not i:
            return Result("", error=f"未找到 {target}")
        if "error" in i:
            return Result(f"{target}: {i['error']}", error=None)
        out = [f"模块 {target} ({i['file']})"]
        if i.get("summary"):
            out.append(f"  摘要: {i['summary']}")
        if i.get("deps"):
            out.append(f"  依赖: {', '.join(i['deps'])}")
        for c in i["classes"]:
            mro = " → ".join(c.get("mro", c["bases"])) or "object"
            out.append(f"  类 {c['name']}: {mro}  {c.get('summary','')}")
            if c.get("methods"):
                out.append(f"    方法: {', '.join(c['methods'])}")
        for f in i["functions"]:
            sig = f.get("signature") or f"({', '.join(f['args'])})"
            out.append(f"  函数 {f['name']}{sig}  {f.get('summary','')}")
        return Result("\n".join(out), error=None)
    if mode == "impact":
        if not target:
            return Result("", error="需要 target= 指定模块名")
        top = target.split(".")[0]
        r = sorted(m for m, i in _cache.items()
                   if "error" not in i and top in i.get("deps", []))
        return ListResult(r, error=None)
    return Result("", error=f"未知 mode: {mode}")
