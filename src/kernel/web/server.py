"""WebSocket + HTTP 服务端：消费 observer 消息队列，推送给浏览器。

隐藏的决策：
  1. asyncio 事件循环 —— 调用者不感知
  2. Queue.get() 同步 → 异步（asyncio.to_thread）
  3. WebSocket / HTTP 路径分发（/ws vs 静态文件）
  4. 消息缓冲 —— 新客户端连接后补发历史消息

接口：serve(observer, host, port) —— 阻塞当前线程。
"""
import asyncio
import json
from pathlib import Path
from queue import Empty

from websockets.asyncio.server import Response, serve as ws_serve
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Headers

_STATIC = Path(__file__).parent / "static"

# MIME types only for what Vite outputs
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _serve_static(path: str):
    """返回静态文件内容 + MIME type，不存在返回 None。"""
    # 安全：拒绝路径穿越
    safe = Path(_STATIC, path.lstrip("/")).resolve()
    if not str(safe).startswith(str(_STATIC.resolve())):
        return None
    if not safe.is_file():
        return None
    return safe.read_bytes(), _MIME.get(safe.suffix, "application/octet-stream")


async def _broadcast(observer, connections, history):
    """循环消费 observer.messages 队列，广播给所有已连接客户端。"""
    while True:
        try:
            msg = await asyncio.to_thread(observer.messages.get, timeout=0.1)
        except Empty:
            await asyncio.sleep(0.05)
            continue

        try:
            data = json.dumps(msg)
        except (TypeError, ValueError):
            continue

        history.append(data)

        if not connections:
            continue

        dead = set()
        for ws in list(connections):
            try:
                await ws.send(data)
            except ConnectionClosed:
                dead.add(ws)
        connections -= dead


async def _process_request(connection, request):
    """HTTP 请求处理：/ws → 升级 WebSocket，/ → index.html，其他 → 静态文件。"""
    path = getattr(request, "path", "/")

    if path == "/ws":
        return None

    # 默认路径 → index.html
    file_path = path if path != "/" else "/index.html"

    result = _serve_static(file_path)
    if result is None:
        return connection.respond(404, "Not Found")

    content, mime = result
    return Response(200, "OK", Headers({"Content-Type": mime}), content)


def serve(observer, host="localhost", port=8765):
    """启动 WebSocket + HTTP 服务，阻塞当前线程。

    前置条件：
      - observer.messages 是 queue.Queue 实例
      - observer.input_queue 是 queue.Queue 实例
      - static/index.html 存在（已构建前端）
    后置条件：/ws 接受 WebSocket 连接，/ 返回 React 前端。
    
    违反前置条件：
      - 缺少 static/index.html 时 raise RuntimeError，提示 cd frontend && npm run build
    """
    from queue import Queue
    assert isinstance(observer.messages, Queue), "observer.messages 必须是 queue.Queue"
    assert isinstance(observer.input_queue, Queue), "observer.input_queue 必须是 queue.Queue"

    if not (_STATIC / "index.html").is_file():
        raise RuntimeError(
            f"静态文件不存在：{_STATIC / 'index.html'}\n"
            f"请先构建前端：cd frontend; npm run build"
        )

    connections = set()
    history = []

    async def ws_handler(websocket):
        connections.add(websocket)
        try:
            for data in history:
                try:
                    await websocket.send(data)
                except ConnectionClosed:
                    connections.discard(websocket)
                    return
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                if msg.get("type") == "input" and "text" in msg:
                    observer.input_queue.put(msg["text"])
                    observer.on_user(msg["text"])
                elif msg.get("type") == "interrupt":
                    observer.interrupt_event.set()
        finally:
            connections.discard(websocket)

    async def run():
        async with ws_serve(
            ws_handler, host, port, process_request=_process_request
        ) as server:
            asyncio.create_task(_broadcast(observer, connections, history))
            await server.serve_forever()

    asyncio.run(run())
