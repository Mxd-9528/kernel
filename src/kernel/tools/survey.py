"""预置函数 survey：测绘项目架构。底层使用 ctags 做符号提取，覆盖 150+ 语言。

缓存自动管理：首次查询自动测绘；项目文件变更（新增/删除/修改）自动失效重扫。
调用者无需关心测绘时机。

用法：
    survey()                            # 全景 str：每模块一行，符号构成 + 依赖
    survey(mode="detail", target="x")   # 单模块 str：符号清单，按 scope 分组
    survey(mode="depends", target="x")  # 正向依赖 list[str]：X 依赖了谁
    survey(mode="impact", target="x")   # 反向依赖 list[str]：谁依赖 X
    survey(mode="hotspots", n=10)       # 被依赖次数降序 list[str]
    survey(path=".")                    # 指定项目根目录
"""

import os
import re
import subprocess
from collections import Counter

from .exclude import _EXCLUDE

# 单一事实源：ctags --list-maps 未覆盖的扩展名映射。
# 同时用于 _source_exts() 和 ctags 命令行 --map-* 参数。
_CTAGS_MAP_OVERRIDES = {
    "TypeScript": [".tsx"],
}

# survey 专属噪声目录：不参与项目架构测绘
_SURVEY_EXCLUDE = frozenset({".claude"})

_cache = {}
_cache_fp = None


def _source_exts():
    """从 ctags --list-maps 动态获取扩展名，叠加 _CTAGS_MAP_OVERRIDES。"""
    exts = set()
    try:
        r = subprocess.run(
            [_find_ctags(), "--list-maps"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.strip().split("\n"):
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            for pat in parts[1].split():
                if pat.startswith("*.") and pat[2:].isalnum():
                    exts.add("." + pat[2:])
    except Exception:
        pass
    for overrides in _CTAGS_MAP_OVERRIDES.values():
        exts.update(overrides)
    return frozenset(exts)


def _ctags_map_args():
    """从 _CTAGS_MAP_OVERRIDES 生成 --map-X=+.ext 参数。"""
    args = []
    for lang, exts in _CTAGS_MAP_OVERRIDES.items():
        for ext in exts:
            args.append(f"--map-{lang}=+{ext}")
    return args


def _find_ctags():
    """定位 ctags 二进制。"""
    home = os.path.expanduser("~/bin")
    candidates = [
        os.path.join(home, "ctags.exe"),
        os.path.join(home, "ctags"),
        "ctags.exe",
        "ctags",
    ]
    for c in candidates:
        try:
            r = subprocess.run([c, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return c
        except Exception:
            continue
    raise RuntimeError(
        "ctags 未找到。安装：brew install universal-ctags / "
        "apt install universal-ctags / "
        "winget install universal-ctags.universal-ctags / "
        "从 https://github.com/universal-ctags/ctags-win32/releases 下载"
    )


def _list_files(path):
    """列出 path 下源码文件，排除噪声目录和编译产物。"""
    exts = _source_exts()
    all_exclude = _EXCLUDE | _SURVEY_EXCLUDE
    files = []
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d not in all_exclude]
        for f in names:
            if os.path.splitext(f)[1].lower() in exts:
                files.append(os.path.join(root, f))
    return files


def _fingerprint(path):
    """(sorted 文件路径元组, max mtime)。"""
    files = sorted(_list_files(os.path.abspath(path)))
    if not files:
        return ((), 0.0)
    return (tuple(files), max(os.path.getmtime(f) for f in files))


def _ensure_cache(path):
    """空缓存或 fingerprint 变化则重扫；否则复用。"""
    global _cache, _cache_fp
    fp = _fingerprint(path)
    if not _cache or _cache_fp != fp:
        _cache = _scan(path)
        _cache_fp = fp


def _scan(path):
    """用 ctags 提取符号，正则提取依赖，构建模块图。"""
    path = os.path.abspath(path)
    ctags = _find_ctags()
    files = _list_files(path)
    if not files:
        return {}

    rel_files = [os.path.relpath(f, path).replace("\\", "/") for f in files]
    file_set = set(rel_files)

    # 1. 运行 ctags：通过 stdin 传文件列表，避免命令行长度限制
    result = subprocess.run(
        [ctags, "-f", "-", "--fields=+klnS"] + _ctags_map_args() + ["-L", "-"],
        input="\n".join(rel_files),
        capture_output=True, text=True, timeout=120,
        cwd=path,
    )

    # 2. 解析 ctags 输出
    # 格式: name<TAB>file<TAB>pattern;"<TAB>kind<TAB>extras...
    symbols_by_file = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name, fpath_rel = parts[0], parts[1].replace("\\", "/")
        kind = parts[3]
        fields = {}
        for f in parts[4:]:
            if ":" in f:
                k, v = f.split(":", 1)
                fields[k] = v

        symbols_by_file.setdefault(fpath_rel, []).append({
            "name": name,
            "kind": kind,
            "line": fields.get("line", "?"),
            "signature": fields.get("signature", ""),
            "scope": fields.get("scope", ""),
            "language": fields.get("language", "?"),
        })

    # 3. 提取依赖
    graph = {}
    for fpath in files:
        rel = os.path.relpath(fpath, path).replace("\\", "/")
        ext = os.path.splitext(rel)[1].lower()
        symbols = symbols_by_file.get(rel, [])

        deps = _extract_deps(fpath, ext, file_set, path)
        graph[rel] = {
            "file": rel,
            "symbols": symbols,
            "deps": deps,
            "language": symbols[0]["language"] if symbols else "?",
        }

    return graph


# ---- 依赖提取 ----

_RE_PY_IMPORT = re.compile(
    r'^\s*(?:from\s+([\w.]+)\s+import\s+([\w.*]+)|import\s+([\w.]+))', re.MULTILINE
)
_RE_TS_IMPORT = re.compile(
    r"""(?:from|import)\s+['"]([^'"]+)['"]""", re.MULTILINE
)
_RE_TS_REQUIRE = re.compile(
    r"""require\(['"]([^'"]+)['"]\)""", re.MULTILINE
)
_RE_GO_IMPORT = re.compile(
    r'import\s+(?:[_\.\w]+\s+)?["]([^"]+)["]', re.MULTILINE
)
_RE_RS_USE = re.compile(
    r'use\s+([\w:]+)', re.MULTILINE
)


def _extract_deps(fpath, ext, file_set, base_path):
    """从文件内容中提取项目内部依赖，返回去扩展名的相对路径列表。"""
    try:
        with open(fpath, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return []

    file_dir = os.path.relpath(os.path.dirname(fpath), base_path).replace("\\", "/")
    raw = []

    if ext == ".py":
        for m in _RE_PY_IMPORT.finditer(content):
            mod_part = m.group(1) or m.group(3)
            if mod_part:
                # from . import X → module is .X
                if mod_part == "." and m.group(2):
                    raw.append("." + m.group(2))
                else:
                    raw.append(mod_part)
    elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"):
        for m in _RE_TS_IMPORT.finditer(content):
            raw.append(m.group(1))
        for m in _RE_TS_REQUIRE.finditer(content):
            raw.append(m.group(1))
    elif ext == ".go":
        for m in _RE_GO_IMPORT.finditer(content):
            raw.append(m.group(1))
    elif ext == ".rs":
        for m in _RE_RS_USE.finditer(content):
            raw.append(m.group(1))

    resolved = set()
    for imp in raw:
        candidates = _resolve_dep(imp, file_dir, ext, file_set)
        resolved.update(candidates)
    return sorted(resolved)


def _resolve_dep(imp, file_dir, ext, file_set):
    """将一条 import 字符串解析为项目内文件路径（去扩展名）。"""
    if imp.startswith("."):
        if imp.startswith("./") or imp.startswith("../"):
            # JS/TS: ./hooks/useWebSocket, ../../foo
            up = 0
            rest = imp
            while True:
                if rest.startswith("../"):
                    up += 1
                    rest = rest[3:]
                elif rest.startswith("./"):
                    rest = rest[2:]
                else:
                    break
            name = rest
        else:
            # Python: .llm, ..observer
            dots = len(imp) - len(imp.lstrip("."))
            up = dots - 1
            name = imp[dots:]
        parent = file_dir
        for _ in range(up):
            parent = os.path.dirname(parent) or "."
        resolved = os.path.join(parent, name).replace("\\", "/")
        return _match_file(resolved, file_set)

    if ext == ".py":
        # 绝对导入：src.kernel.agent → src/kernel/agent.py
        candidate = imp.replace(".", "/") + ".py"
        if candidate in file_set:
            return {candidate}
        # 也尝试 __init__.py
        candidate = imp.replace(".", "/") + "/__init__.py"
        if candidate in file_set:
            return {candidate}

    if ext == ".rs":
        if imp.startswith("crate::"):
            candidate = imp.replace("crate::", "src/").replace("::", "/") + ".rs"
            if candidate in file_set:
                return {candidate}

    if ext == ".go":
        # 尝试将 import 路径映射到项目文件
        parts = imp.split("/")
        candidate = imp + ".go"
        if candidate in file_set:
            return {candidate}

    return set()


def _match_file(resolved, file_set):
    """尝试 resolved 路径加 _source_exts() 中的所有扩展名，返回匹配的集合。"""
    for ext in sorted(_source_exts()):
        c = resolved + ext
        if c in file_set:
            return {c}
    # 尝试 index 文件（仅对常见前端/后端扩展名）
    for ext in (".py", ".ts", ".tsx", ".js", ".jsx"):
        c = resolved + "/index" + ext
        if c in file_set:
            return {c}
    return set()


# ---- 查询模式 ----

def survey(mode="overview", target=None, path=".", n=10):
    """测绘项目架构：符号构成、模块依赖、变更影响面。

    需要理解项目结构、追踪依赖链、评估改动波及范围时使用。

    survey()                            — 全景 str：每模块一行
    survey(mode="detail", target=X)     — 单模块 str：符号清单
    survey(mode="depends", target=X)    — 正向依赖 list[str]
    survey(mode="impact", target=X)     — 反向依赖 list[str]
    survey(mode="hotspots", n=10)       — 被依赖次数降序 list[str]
    survey(path=".")                    — 指定项目根目录
    """
    _ensure_cache(path)

    if mode == "overview":
        return _mode_overview()

    if mode == "detail":
        if not target:
            raise ValueError("需要 target= 指定模块名")
        target, info = _resolve_target(target)
        return _mode_detail(target, info)

    if mode == "depends":
        if not target:
            raise ValueError("需要 target= 指定模块名")
        target, info = _resolve_target(target)
        return list(info.get("deps", []))

    if mode == "impact":
        if not target:
            raise ValueError("需要 target= 指定模块名")
        return _mode_impact(target)

    if mode == "hotspots":
        return _mode_hotspots(n)

    raise ValueError(
        f"未知 mode: {mode}. 支持: overview, detail, depends, impact, hotspots"
    )


def _resolve_target(target):
    """模糊匹配目标模块名，返回 (模块路径, graph字典)。

    匹配优先级：精确匹配 > 以 target 结尾 > 包含 target。
    """
    target = target.replace("\\", "/")
    info = _cache.get(target)
    if info:
        return target, info
    # 1. 精确匹配文件名（不含目录）
    for k in _cache:
        if os.path.basename(k) == target:
            return k, _cache[k]
    # 2. 以 target 结尾（如 "agent.py"）
    for k in _cache:
        if k.endswith("/" + target) or k.endswith(target):
            return k, _cache[k]
    # 3. 包含
    for k in _cache:
        if target in k:
            return k, _cache[k]
    raise ValueError(f"未找到 {target}")


def _mode_overview():
    lines = []
    for m in sorted(_cache):
        info = _cache[m]
        syms = info["symbols"]
        if not syms:
            lines.append(f"{m}  [无符号]")
            continue

        kind_counts = Counter(s["kind"] for s in syms)
        parts = []
        for kind, count in sorted(kind_counts.items()):
            short = kind
            parts.append(f"{count}{short}")
        kind_str = "/".join(parts)

        dep_str = ""
        if info["deps"]:
            dep_names = []
            for d in info["deps"]:
                segs = d.replace("\\", "/").split("/")
                dep_names.append("/".join(segs[-2:]) if len(segs) > 2 else d)
            dep_str = " →" + ",".join(dep_names[:5])
            if len(dep_names) > 5:
                dep_str += f" …+{len(dep_names)-5}"

        lines.append(f"{m} ({kind_str}){dep_str}")

    return "\n".join(lines)


def _mode_detail(target, info):
    syms = info["symbols"]
    out = [f"模块 {target}"]
    if info["language"] != "?":
        out.append(f"  语言: {info['language']}")
    if info["deps"]:
        out.append(f"  依赖: {', '.join(info['deps'])}")

    top_level = []
    scoped = {}
    for s in syms:
        entry = (s["name"], s["kind"], s["signature"])
        if s["scope"]:
            scoped.setdefault(s["scope"], []).append(entry)
        else:
            top_level.append(entry)

    if top_level:
        out.append("  顶层符号:")
        for name, kind, sig in top_level:
            sig_str = str(sig) if sig and sig != "()" else ""
            out.append(f"    {kind} {name}{sig_str}")

    for scope, entries in sorted(scoped.items()):
        out.append(f"  {scope}:")
        for name, kind, sig in entries:
            sig_str = str(sig) if sig and sig != "()" else ""
            out.append(f"    {kind} {name}{sig_str}")

    return "\n".join(out)


def _mode_impact(target):
    target = target.replace("\\", "/")
    result = []
    for m, info in _cache.items():
        for d in info.get("deps", []):
            if d == target or d.endswith("/" + target) or target in d:
                result.append(m)
                break
    return sorted(result)


def _mode_hotspots(n):
    dep_count = {}
    for m, info in _cache.items():
        for d in info.get("deps", []):
            dep_count[d] = dep_count.get(d, 0) + 1
    ranked = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)
    return [f"{m} ({count} dependents)" for m, count in ranked[:n]]
