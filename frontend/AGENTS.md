# frontend/ AGENTS.md

Vite + React + TypeScript。开发时通过 `/ws` 代理连后端 WebSocket。

## Essential Commands

```bash
npm install                 # 装依赖（仅首次）
npm run dev                 # dev server（5173，/ws 代理到 8765）
npm run build               # 构建 → ../src/kernel/web/static/
npm test                    # vitest
npx tsc -b --noEmit         # 类型检查
```

## 目录约定

- `src/App.tsx` — 顶层
- `src/components/` — UI 组件（一个文件一个组件）
- `src/hooks/` — 自定义 hook（`useWebSocket.ts` 封装 JSON-RPC）
- `src/types.ts` — 共享类型
- `tests/` — 测试文件（**不在 `src/`**）

## 不读代码就不知道的

- **测试目录在 `frontend/tests/` 而非 `src/tests/`**——Vite 模块解析要求测试在 Vite 根目录内。
- **构建输出到 `../src/kernel/web/static/`**——`vite.config.ts` 已配置，Python 端 `server.py` 静态伺服直接读该路径，构建后无需任何 Python 侧改动。
- **dev 模式的 `/ws` 代理到 `localhost:8765`**——需先 `ma --web` 起后端。

## 消息协议

见 [../src/kernel/web/AGENTS.md](../src/kernel/web/AGENTS.md)。
