# 方案 C：IPC 进程分离

**状态：📋 远期规划**

## 思路

比方案 B 更进一步——agent 进程不负责任何显示，只通过标准协议（JSON-RPC over stdin/stdout 或 TCP）输出事件流。前端是完全独立的进程，可以是终端应用、GUI 应用、Web 应用、VS Code 扩展、甚至另一个 AI agent。两者通过 IPC 通信。

## 架构图

```
┌─────────────────┐     JSON-RPC / stdin/stdout     ┌──────────────────┐
│  kernel 后端     │ ──────────────────────────────→ │  前端进程         │
│  (agent.py)      │ ←────────────────────────────── │  (任意语言)        │
│                  │                                  │                   │
│  - agent 循环    │                                  │  - 终端前端       │
│  - 上下文压缩    │                                  │  - Web 前端       │
│  - 历史持久化    │                                  │  - VS Code 扩展   │
│  - 文件操作      │                                  │  - GUI 应用       │
│  - 代码执行      │                                  │  - 另一个 agent   │
└─────────────────┘                                  └──────────────────┘
```

## 协议设计

采用 JSON-RPC 2.0，与 LSP 协议的设计思想一致：

```json
// 后端 → 前端：通知
{"jsonrpc":"2.0", "method":"window/thinking", "params":{"token":"..."}}
{"jsonrpc":"2.0", "method":"window/delta", "params":{"token":"..."}}
{"jsonrpc":"2.0", "method":"window/flush", "params":{}}
{"jsonrpc":"2.0", "method":"window/display", "params":{"content":"..."}}

// 前端 → 后端：请求
{"jsonrpc":"2.0", "id":1, "method":"chat/send", "params":{"text":"读 agent.py"}}
{"jsonrpc":"2.0", "id":2, "method":"chat/new", "params":{}}
{"jsonrpc":"2.0", "id":3, "method":"chat/model", "params":{"model":"ark-code"}}

// 后端 → 前端：响应
{"jsonrpc":"2.0", "id":1, "result":{"status":"ok"}}
```

## 与方案 B 的关系

方案 B 是方案 C 的前端实现之一。方案 B 的 WebSocket 消息格式可以平滑迁移到 JSON-RPC：

```
方案 B: {"type":"delta","token":"..."}
方案 C: {"jsonrpc":"2.0","method":"window/delta","params":{"token":"..."}}
```

迁移路径：方案 B 上线后，将 WebSocket 消息格式改为 JSON-RPC 2.0。此时后端的协议层已经标准化，前端可以独立开发——终端前端、Web 前端、VS Code 扩展前端都可以连接到同一个后端。

## 价值

方案 C 的价值不在当前——当前只有一个前端。它的价值在于"未来可以有多个前端"。当以下场景出现时，IPC 模式的价值兑现：

- VS Code 插件开发者想为 kernel 做一个原生面板
- 有人想用 Go/Rust 写一个极速的终端前端
- 有人想把 kernel 集成到自己的工具链中
- 多个前端同时连接同一个 agent 会话（协作场景）

## 与方案 B 的时间线

- **现在**：方案 B（WebSocket + Web 前端）
- **方案 B 稳定后**：将 WebSocket 消息格式标准化为 JSON-RPC 2.0
- **有需求时**：开发其他前端客户端（VS Code 扩展、GUI 应用等）
- **长期**：kernel 后端完全脱离对任何前端的假设，成为纯协议服务

## 不现在做的原因

1. **当前只有一个前端需求**。IPC 的复杂度（协议定义、错误处理、连接管理、版本协商）只有在多前端场景下才有收益。
2. **方案 B 已经是前进方向**。WebSocket 和 JSON-RPC 之间只有格式差异，不是架构差异。先跑通方案 B，再标准化为 JSON-RPC。
3. **过早标准化是浪费**。在只有一个实现者的情况下定义"标准协议"，大概率会定义出只有自己能用的协议。等第二个前端出现时再定义——那时知道什么需要标准、什么不需要。
