"""系统自描述：扫描 tools/ 和 skills/，组装系统提示词。

manifest 和 skills 共有的逻辑（扫目录 → 抽元信息 → 拼 prompt）合并在此。
单一事实源，改函数即改描述——不手写 schema。
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Callable

from . import tools

_SKILLS_DIR = Path(__file__).parent / "skills"


# ── tools/ 扫描 ──────────────────────────────────────────────────


def presets() -> list[tuple[str, Callable]]:
    """扫 tools/，返回 [(name, func), ...]：每个模块里与模块同名的函数。"""
    out = []
    for info in pkgutil.iter_modules(tools.__path__):
        mod = importlib.import_module(f"kernel.tools.{info.name}")
        func = getattr(mod, info.name, None)
        if inspect.isfunction(func):
            out.append((info.name, func))
    return sorted(out)


def list_tools() -> str:
    """拼成 prompt 用的预置函数清单：name(签名) + 完整 docstring。"""
    lines = []
    for name, func in presets():
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""
        indented = "\n".join("  " + ln for ln in doc.splitlines())
        lines.append(f"- {name}{sig}\n{indented}")
    return "\n".join(lines)


# ── skills/ 扫描 ──────────────────────────────────────────────────


def _meta(skill_md: Path) -> dict | None:
    """从 SKILL.md 的 YAML frontmatter 取字段。"""
    import yaml
    text = skill_md.read_text("utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        meta = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def skills(directory: Path = _SKILLS_DIR) -> list[tuple[str, str]]:
    """扫 skills/，返回 [(name, description), ...]。无目录或缺 frontmatter 的跳过。"""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    out = []
    for sub in sorted(directory.iterdir()):
        md = sub / "SKILL.md"
        if not md.is_file():
            continue
        meta = _meta(md)
        if meta and "name" in meta and "description" in meta:
            out.append((meta["name"], meta["description"]))
    return out


def list_skills(directory: Path = _SKILLS_DIR) -> str:
    """拼成 prompt 用的技能清单。空则返回空串。"""
    items = skills(directory)
    if not items:
        return ""
    lines = ["技能在 skills/<名字>/SKILL.md，需要时用 read() 加载正文："]
    lines += [f"- {name}：{desc}" for name, desc in items]
    return "\n".join(lines)


# ── 系统提示组装 ──────────────────────────────────────────────────


def build_system() -> str:
    """组装完整系统提示词：prompt.md + 预置函数清单 + 技能清单 + 可选项目根 AGENTS.md。"""
    here = Path(__file__).parent
    out = (here / "prompt.md").read_text("utf-8") + \
          "\n\n# 预置函数（已注入命名空间，直接调用，无需 import）\n\n" + list_tools()
    sk = list_skills()
    if sk:
        out += "\n\n# 技能\n\n" + sk
    # 项目根 AGENTS.md：AI 阅读入口（分层导航 + 硬规则 + 宪法索引）
    agents_path = here.parent.parent / "AGENTS.md"
    if agents_path.exists():
        out += "\n\n" + agents_path.read_text("utf-8")
    return out
