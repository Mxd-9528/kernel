"""决策-执行-观察 循环。"""
from __future__ import annotations

import threading

from .observer import BaseObserver, Observer

from . import llm
from . import runtime
from . import compact
from . import history

# ── 模型响应 ──────────────────────────────────────────────────

class Response:
    """模型响应：封装文本内容，延迟提取代码块。"""

    def __init__(self, content: str) -> None:
        self.content = content

    def has_code(self) -> bool:
        return bool(runtime.extract_blocks(self.content))

    @property
    def code(self) -> list[str]:
        return runtime.extract_blocks(self.content)


def stream_model(messages: list[dict], model: str | None = None, *, observer: Observer | None = None, stop_event: threading.Event | None = None) -> Response:
    """流式调用 LLM，逐 token 通知 observer，返回 Response。
    
    stop_event: threading.Event | None。若被设置，token 循环立即终止，
                on_flush() 仍被调用，返回已累积内容。
    """
    if observer is None:
        observer = BaseObserver()
    content = ""
    finish_reason: str | None = None
    try:
        for kind, token in llm.stream_chat(messages, model):
            if stop_event and stop_event.is_set():
                break
            if kind == "thinking":
                observer.on_thinking(token)
            elif kind == "finish":
                finish_reason = token
            else:  # "content"
                content += token
                observer.on_delta(token)
    except Exception as e:
        # 保留已累积 content，追加错误告警（原逻辑用错误字符串完全覆盖 content，会丢失流式已生成内容）
        warn = f"\n\n⚠️ [LLM 请求失败: {e}]"
        content += warn
        observer.on_delta(warn)
    else:
        # 正常结束但终止原因异常：追加可见告警
        if finish_reason and finish_reason != "stop":
            warn = f"\n\n⚠️ [响应被截断: finish_reason={finish_reason}]"
            content += warn
            observer.on_delta(warn)
    finally:
        observer.on_flush(content)
    return Response(content)


def execute_code(code_blocks: list[str]) -> str:
    """执行代码块，返回环境反馈文本。"""
    return runtime.feedback(runtime.execute_blocks(code_blocks))


# ── 核心循环 ──────────────────────────────────────────────────

_MAX_ITERS = 20


def agent(prompt: str, *, messages: list[dict] | None = None, model: str | None = None, stop_event: threading.Event | None = None, max_iters: int = _MAX_ITERS, observer: Observer | None = None) -> list[dict]:
    """决策-执行-观察 循环。"""
    if observer is None:
        observer = BaseObserver()
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": prompt})

    for _ in range(max_iters):
        if stop_event and stop_event.is_set():
            break

        messages[:] = compact.compact(messages, model=model)   # 上下文压缩（纯后端逻辑）

        response = stream_model(messages, model, observer=observer, stop_event=stop_event)  # → display 流式渲染
        messages.append({"role": "assistant", "content": response.content})
        history.save(messages)                          # 持久化（纯后端逻辑）

        if not response.has_code():
            return messages

        feedback = execute_code(response.code)
        messages.append({"role": "user", "content": feedback})
        history.save(messages)                          # 持久化（纯后端逻辑）

    return messages