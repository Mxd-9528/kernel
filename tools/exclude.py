"""全局排除规则：tools/ 下各搜索工具共享的噪声排除清单。

目录级排除：版本控制、虚拟环境、缓存目录、构建产物。
文件级排除：编译产物、历史文件（避免 grep 命中自己写过的搜索词）。
"""

_EXCLUDE = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", ".eggs",
})

# 文件级噪声：编译产物、agent 自身对话历史
_EXCLUDE_FILES = ("*.pyc", "*.pyo", "history.json")
