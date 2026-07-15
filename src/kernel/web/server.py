"""WebSocket + HTTP 服务端：消费 observer 消息队列，推送给浏览器。

隐藏的决策：
  1. asyncio 事件循环 —— 调用者不感知
  2. Queue.get() 同步 → 异步（asyncio.to_thread）
  3. WebSocket / HTTP 路径分发（/ vs /ws vs 其他）
  4. 消息缓冲 —— 新客户端连接后补发历史消息

接口：serve(observer, host, port) —— 阻塞当前线程。
"""
import asyncio
import json
from pathlib import Path
from queue import Empty

from websockets.asyncio.server import serve as ws_serve
from websockets.exceptions import ConnectionClosed

# 模块加载时缓存 HTML，避免每次请求读磁盘
_HTML = None

def _load_html():
    global _HTML
    if _HTML is None:
        p = Path(__file__).parent / "frontend.html"
        _HTML = p.read_text("utf-8") if p.exists() else None
    return _HTML


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
    """HTTP 请求处理：/ → frontend.html，/ws → 升级 WebSocket，其他 → 404。"""
    path = getattr(request, "path", "/")

    if path == "/":
        html = _load_html()
        if html is None:
            return connection.respond(404, "frontend.html not found")
        response = connection.respond(200, html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    if path == "/ws":
        return None

    return connection.respond(404, "Not Found")


def serve(observer, host="localhost", port=8765):
    """启动 WebSocket + HTTP 服务，阻塞当前线程。

    前置条件：
      - observer.messages 是 queue.Queue 实例
      - observer.input_queue 是 queue.Queue 实例
      - frontend.html 存在于模块同目录
    后置条件：/ws 接受 WebSocket 连接，队列消息 JSON 广播；/ 返回 HTML。
    """
    from queue import Queue
    assert isinstance(observer.messages, Queue), "observer.messages 必须是 queue.Queue"
    assert isinstance(observer.input_queue, Queue), "observer.input_queue 必须是 queue.Queue"
    assert _load_html() is not None, "frontend.html 不存在"

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
        finally:
            connections.discard(websocket)

    async def run():
        async with ws_serve(
            ws_handler, host, port, process_request=_process_request
        ) as server:
            asyncio.create_task(_broadcast(observer, connections, history))
            await server.serve_forever()

    asyncio.run(run())
