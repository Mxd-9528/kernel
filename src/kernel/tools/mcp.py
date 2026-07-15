"""预置函数 mcp：连接 MCP 服务器，列出或调用工具。

每次调用起一次新进程，走完整 JSON-RPC 握手。无 session 持久化——
MCP 服务器设计上就是轻量可快速重启的。若需连续调用同一服务器多次，
模型可自己用 subprocess.Popen 起进程保持 session。

配置：在 ~/.kernel/mcp.json 中预设服务器别名。
"""

import json
import os
import subprocess


def _config():
    """读 ~/.kernel/mcp.json，返回 dict（别名 → 命令）。文件不存在或格式错误返回空 dict。"""
    try:
        with open(os.path.expanduser("~/.kernel/mcp.json"), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _resolve(server):
    """若 server 是 ~/.kernel/mcp.json 中的别名，返回对应的命令字符串；否则原样返回。"""
    cfg = _config()
    return cfg.get(server, server)


def _mcp_call(proc, req):
    """向 MCP 进程发一个 JSON-RPC 请求，等回对应 id 的响应（跳过中间通知）。"""
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        resp = json.loads(line)
        if resp.get("id") == req.get("id"):
            return resp


def mcp(server, tool=None, **params):
    """连接 MCP 服务器。tool=None 列出工具；tool=X 调用该工具。

    server: 启动命令或 ~/.kernel/mcp.json 中的别名
    tool: 工具名。None 时返回工具列表（含每个工具的 description 和参数 schema）
    params: 工具参数，如 path="/tmp/x.txt"

    返回值：
      tool=None → list[dict]，每个 dict 含 name / description / inputSchema
      tool=X → dict，工具返回结果（含 content 等 MCP 标准字段）

    失败时 raise（JSON-RPC 错误或 subprocess 错误）。
    """
    cmd = _resolve(server)
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _mcp_call(proc, {
            "jsonrpc": "2.0", "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "kernel", "version": "1.0"},
            },
        })

        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        if tool is None:
            resp = _mcp_call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            return resp["result"]["tools"]

        resp = _mcp_call(proc, {
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {"name": tool, "arguments": params},
        })
        return resp["result"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
