# kernel

持久 IPython 内核的自驱动 agent。模型通过写 `<EXEC>` Python 代码块来感知和改变环境——回代码 → 执行 → 看反馈 → 再回代码 → 直到做完。

不是「工具调用」范式。预置函数只是预加载进内核命名空间的普通函数，不够用直接写 Python。

> [CONSTITUTION.md](CONSTITUTION.md) 是设计原则；[AGENTS.md](AGENTS.md) 是 AI 阅读入口（自动加载，分层导航到各子目录的 AGENTS.md）。

## 前置条件

- Python 3.8+
- Node.js 18+（仅 Web 面板需要）

## 终端对话

```bash
git clone ...
cd kernel
pip install -e .            # 安装 Python 依赖，创建 ma 命令

# 配 models.json（API 地址 + 模型名）和 .env（API key）

ma                          # 开始对话
```

## Web 面板

一次构建，之后 `ma --web` 全搞定（端口 8765）：

```bash
cd frontend
npm install                 # 仅首次：装前端依赖
npm run build               # 构建 → src/kernel/web/static/

cd ..
ma --web                    # 启动服务端
# 浏览器打开 http://localhost:8765
```

开发时想用热更新：

```bash
# 终端 1：ma --web
# 终端 2：cd frontend; npm run dev
# 浏览器打开 http://localhost:5173（Vite 代理 WebSocket 到 8765）
```

对话内命令：

| 命令 | 作用 |
|---|---|
| `exit` | 退出 |
| `/new` | 清空历史，开一段新对话 |
| `/model <名>` | 切换模型（不带名则显示当前+可选） |

## 测试

```bash
# Python
python -m pytest tests/     # 32 个测试
ruff check src/ tests/      # 代码检查

# 前端
cd frontend
npm test                   # vitest
npx tsc -b --noEmit        # TypeScript 类型检查
```