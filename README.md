# kernel

持久 IPython 内核的自驱动 agent。模型通过写 `<EXEC>` Python 代码块来感知和改变环境——回代码 → 执行 → 看反馈 → 再回代码 → 直到做完。

不是「工具调用」范式。预置函数只是预加载进内核命名空间的普通函数，不够用直接写 Python。

> [CONTEXT.md](CONTEXT.md) 是设计哲学（给 AI 和人类）；[CLAUDE.md](CLAUDE.md) 是操作手册（给 AI）。这份给人看。

## 跑起来

```bash
pip install -e .            # 装依赖
ma                          # 终端对话
ma --web                    # 启动 WebSocket 后端（端口 8765）
```

浏览器面板（需先 `ma --web`）：

```bash
cd frontend && npm install     # 仅首次：装前端依赖
cd frontend && npm run dev     # 启动 Vite dev server（端口 5173）
# 浏览器打开 http://localhost:5173
```

对话内命令：

| 命令 | 作用 |
|---|---|
| `exit` | 退出 |
| `/new` | 清空历史，开一段新对话 |
| `/model <名>` | 切换模型（不带名则显示当前+可选） |

> `models.json` 配 url/key_env/model。**默认模型 = 文件第一个**，换默认就把想要的挪到最前。key 值存 `.env`。

## 加一个预置函数

在 `tools/` 写 `x.py`，里面 `def x(...)` 带 docstring，返回 `Result`。自动发现并注入内核。

## 加一个技能

在 `skills/` 建 `<名字>/SKILL.md`，开头写 YAML frontmatter（`name:` / `description:`）。自动发现，模型需要时自己 `read` 加载正文（不预加载，省 token）。

## 测试

```bash
# Python
python -m pytest tests/     # 32 个测试
ruff check src/ tests/      # 代码检查

# 前端
cd frontend && npm test        # vitest
cd frontend && npx tsc -b --noEmit  # TypeScript 类型检查
```