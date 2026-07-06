"""预置函数 plan：跨轮任务计划（整表覆盖式 TODO）。

设计洞察沿用 Codex update_plan：一个函数、一份整表、三态、无 id、prompt 层管纪律。
返回格式化的整表字符串；失败通过 raise 传递（ValueError / TypeError）。
"""

_VALID = {"pending", "in_progress", "completed"}
_MARK = {"pending": "☐", "in_progress": "▸", "completed": "✔"}


def plan(items):
    """维护跨轮 TODO 列表。整表覆盖，每次给完整列表。返回格式化的整表字符串。

    调用格式：
        plan([
            {"text": "读需求", "status": "completed"},
            {"text": "写实现", "status": "in_progress"},
            {"text": "跑测试", "status": "pending"},
        ])

    何时用：任务跨多轮、有逻辑阶段，或用户一句话要求做多件事。
    何时不用：单步任务直接做；不用填充步骤拉长；不列你做不到的事。

    维护：
    - 始终恰好一个 in_progress（不批量跳状态）
    - 结束前所有项应为 completed 或明确取消
    - 调用后不复述计划全文——返回值已含格式化整表

    示例：
        好：1. Add CLI entry with file args  2. Parse Markdown via CommonMark  ...
        差：1. Create CLI tool  2. Add parser  3. Convert to HTML  （太笼统、无验证锚点）

    每步 5-7 字，简短描述任务。status 三种：pending / in_progress / completed。
    """
    if not isinstance(items, list):
        raise TypeError(f"items 必须是 list，得到 {type(items).__name__}")
    lines = []
    for item in items:
        text = item.get("text", "").strip()
        status = item.get("status", "pending")
        if status not in _VALID:
            raise ValueError(f"未知状态 {status!r}，须为 pending / in_progress / completed")
        lines.append(f"{_MARK[status]} {text}")
    return "\n".join(lines) if lines else "(计划为空)"
