# kernel

持久 IPython 内核上的极简自驱动 agent。模型通过写 Python 代码块来感知和改变环境——回代码 → 执行 → 看反馈 → 再回代码 → 直到说做完。

不是「工具调用」范式。预置函数只是预加载进内核命名空间的普通函数，不够用直接写 Python。

> [CONTEXT.md](CONTEXT.md) 给 AI 读的设计哲学；[CLAUDE.md](CLAUDE.md) 给 Claude Code 的操作手册。这份给人看。

## 跑起来

```bash
pip install -e .          # 装依赖（ipython, rich, pyyaml）
python chat.py            # 启动对话，默认模型 = models.json 第一个
python chat.py ark-code   # 指定模型（名取自 models.json）
```

对话内斜杠命令：

| 命令 | 作用 |
|---|---|
| `exit` | 退出 |
| `/new` | 清空历史，开一段新对话 |
| `/model <名>` | 切换模型（不带名则显示当前+可选） |

> `models.json` 里配置模型的 url/key_env/model。**默认模型 = 文件里第一个**，换默认就把想要的挪到最前。key 真值存 `.env`（不进 git），`models.json` 只存环境变量名。

## 加一个预置函数

在 `tools/` 写 `x.py`，里面 `def x(...)` 带 docstring，返回 `Result`。完事——`manifest` 自动扫到它并注入。

## 加一个技能

在 `skills/` 建 `<名字>/SKILL.md`，开头写 YAML frontmatter（`name:` / `description:`）。完事——`skills.py` 自动扫到它，模型需要时自己 `read` 加载正文（不预加载，省 token）。

## 测试

```bash
python tests.py          # 跑全部
python tests_tools.py    # 只跑工具测试
uvx ruff check .         # 静态检查（目标 Python 3.8）
```
