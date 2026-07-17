"""预置函数 agent：后台运行子代理循环，f.result() 返回最终纯文本报告。"""

from __future__ import annotations

import os
import re
import tempfile
import threading
from concurrent.futures import Future

from .. import llm
from .. import runtime

_MAX_ITERS = 20


def _run_subagent(task: str, model: str | None) -> str:
    from ..system import build_system

    system_prompt = build_system()
    # 排除 agent 自身，避免子代理递归调用
    system_prompt = re.sub(r'^- agent\(.+\n(?:  .*\n)*', '', system_prompt, flags=re.MULTILINE)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]
    old_cwd = os.getcwd()
    text = ""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            for _ in range(_MAX_ITERS):
                try:
                    text = "".join(
                        token for kind, token in llm.stream_chat(messages, model)
                        if kind == "content"
                    )
                except Exception as e:
                    return f"子代理 LLM 请求失败: {e}"
                messages.append({"role": "assistant", "content": text})
                blocks = runtime.extract_blocks(text)
                if not blocks:
                    return text
                feedback = runtime.feedback(runtime.execute_blocks(blocks))
                messages.append({"role": "user", "content": feedback})
            return text
        finally:
            os.chdir(old_cwd)


def agent(task: str, *, model: str | None = None) -> Future[str]:
    """起后台子代理执行 task，立即返回 Future。后台运行，完成后不会主动通知——需主动调用 f.result() 获取最终纯文本报告。

    探索性任务（研究、调研、多步推理）交给子代理，避免污染父代理上下文。
    """
    fut: Future[str] = Future()

    def target() -> None:
        if not fut.set_running_or_notify_cancel():
            return
        try:
            fut.set_result(_run_subagent(task, model))
        except BaseException as e:
            fut.set_exception(e)

    threading.Thread(target=target, daemon=True).start()
    return fut
