"""决策-执行-观察 循环 + 事件钩子系统。"""
import llm
import runtime

# ── 事件钩子 ──────────────────────────────────────────────────

_hooks = {}

# ── 事件常量：emit / on 共用，避免裸字符串拼写错误 ──────────────────

EVENT_THINKING = "thinking_delta"
EVENT_DISPLAY = "display_delta"
EVENT_FLUSH = "display_flush"
EVENT_BEFORE_SEND = "before_send"
EVENT_SAVE = "save"
EVENT_DISPLAY_MSG = "display"

def on(event):
    """注册事件处理器。"""
    def decorator(fn):
        _hooks.setdefault(event, []).append(fn)
        return fn
    return decorator

def emit(event, *args, **kwargs):
    """触发事件，依次调用所有已注册的处理器。"""
    for fn in _hooks.get(event, []):
        fn(*args, **kwargs)


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


def stream_model(messages, model=None):
    """流式调用 LLM，逐 token 触发 thinking_delta / display_delta，返回 Response。"""
    content = ""
    try:
        for kind, token in llm.stream_chat(messages, model):
            if kind == "thinking":
                emit(EVENT_THINKING, token)
            else:
                content += token
                emit(EVENT_DISPLAY, token)
        emit(EVENT_FLUSH)
    except Exception as e:
        emit(EVENT_FLUSH)
        content = f"LLM 请求失败: {e}"
    return Response(content)


def execute_code(code_blocks):
    """执行代码块，返回环境反馈文本。"""
    return runtime.feedback(runtime.execute_blocks(code_blocks))


# ── 核心循环 ──────────────────────────────────────────────────

_MAX_ITERS = 20


def agent(prompt, *, messages=None, model=None, stop_event=None, max_iters=_MAX_ITERS):
    """决策-执行-观察 循环。"""
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": prompt})

    for _ in range(max_iters):
        if stop_event and stop_event.is_set():
            break

        emit(EVENT_BEFORE_SEND, messages, model)          # → compact 压缩

        response = stream_model(messages, model)       # → display 流式渲染
        messages.append({"role": "assistant", "content": response.content})
        emit(EVENT_SAVE, messages)                         # → history 存盘

        if not response.has_code():
            return messages

        feedback = execute_code(response.code)
        messages.append({"role": "user", "content": feedback})
        emit(EVENT_SAVE, messages)                         # → history 存盘

    return messages