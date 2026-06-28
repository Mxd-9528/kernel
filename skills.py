"""自动扫描 skills/ 生成技能清单——和 manifest 同模式（扫目录、抽元信息、拼 prompt）。

只列「名字 + 描述」进 prompt，正文不预加载——模型需要哪个自己 read skills/名字/SKILL.md。
渐进式披露：prompt 只放索引，省 token。SKILL.md 用 YAML frontmatter（name/description），用 yaml 解析。
"""

from pathlib import Path

_DIR = Path(__file__).parent / "skills"


def _meta(skill_md):
    """从 SKILL.md 的 YAML frontmatter 取字段。用 yaml 正确处理多行值/嵌套/引号，不手写残缺解析。"""
    import yaml
    text = skill_md.read_text("utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)  # 第二个 --- 是 frontmatter 结尾
    if end == -1:
        return None
    try:
        meta = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def skills(directory=_DIR):
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


def list_skills(directory=_DIR):
    """拼成 prompt 用的技能清单。空则返回空串。"""
    items = skills(directory)
    if not items:
        return ""
    lines = ["技能在 skills/<名字>/SKILL.md，需要时用 read() 加载正文："]
    lines += [f"- {name}：{desc}" for name, desc in items]
    return "\n".join(lines)
