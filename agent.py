"""决策-执行-观察 循环。"""
from observer import Observer, CompositeObserver, BaseObserver

import llm
import runtime

# ── 模型响应 ──────────────────────────────────────────────────

class Response:
    """模型响应：封装文本内容，延迟提取代码块。"""

    def __init__(self, content):
        self.content = content

    def has_code(self):
        return bool(runtime.extract_blocks(self.content))

    @property
    def code(self):
        return runtime.extract_blocks(self.content)


def stream_model(messages, model=None, *, observer=None):
    """流式调用 LLM，逐 token 通知 observer，返回 Response。"""
    if observer is None:
        observer = BaseObserver()
    content = ""
    try:
        for kind, token in llm.stream_chat(messages, model):
            if kind == "thinking":
                observer.on_thinking(token)
            else:
                content += token
                observer.on_delta(token)
        observer.on_flush()
    except Exception as e:
        observer.on_flush()
        content = f"LLM 请求失败: {e}"
    return Response(content)


def execute_code(code_blocks):
    """执行代码块，返回环境反馈文本。"""
    return runtime.feedback(runtime.execute_blocks(code_blocks))


# ── 核心循环 ──────────────────────────────────────────────────

_MAX_ITERS = 20


def agent(prompt, *, messages=None, model=None, stop_event=None, max_iters=_MAX_ITERS, observer=None):
    """决策-执行-观察 循环。"""
    if observer is None:
        observer = BaseObserver()
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": prompt})

    for _ in range(max_iters):
        if stop_event and stop_event.is_set():
            break

        observer.before_send(messages, model)          # → compact 压缩

        response = stream_model(messages, model, observer=observer)  # → display 流式渲染
        messages.append({"role": "assistant", "content": response.content})
        observer.save(messages)                         # → history 存盘

        if not response.has_code():
            return messages

        feedback = execute_code(response.code)
        messages.append({"role": "user", "content": feedback})
        observer.save(messages)                         # → history 存盘

    return messages