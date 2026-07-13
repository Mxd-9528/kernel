"""预置函数 agent：后台运行子代理循环，join() 返回最终纯文本报告。"""

import os
import re
import tempfile
import threading

import llm
import runtime

_MAX_ITERS = 20


class _SubAgentThread(threading.Thread):
    """子代理线程，join() 返回最终纯文本报告。"""

    def __init__(self, task, model=None):
        super().__init__(daemon=True)
        self._task = task
        self._model = model
        self._result = None

    def run(self):
        from system import build_system

        system_prompt = build_system()
        # 排除 agent 自身，避免子代理递归调用
        system_prompt = re.sub(r'^- agent\(.+\n(?:  .*\n)*', '', system_prompt, flags=re.MULTILINE)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._task},
        ]
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                for _ in range(_MAX_ITERS):
                    try:
                        text = "".join(
                            token for kind, token in llm.stream_chat(messages, self._model)
                            if kind == "content"
                        )
                    except Exception as e:
                        self._result = f"子代理 LLM 请求失败: {e}"
                        return
                    messages.append({"role": "assistant", "content": text})
                    blocks = runtime.extract_blocks(text)
                    if not blocks:
                        self._result = text
                        return
                    feedback = runtime.feedback(runtime.execute_blocks(blocks))
                    messages.append({"role": "user", "content": feedback})
                self._result = text
            finally:
                os.chdir(old_cwd)

    def join(self, timeout=None):
        super().join(timeout)
        return self._result


def agent(task, *, model=None):
    """起后台子代理执行 task，立即返回 Thread。调用 t.join() 获取最终纯文本报告。

    探索性任务（研究、调研、多步推理）交给子代理，避免污染父代理上下文。
    """
    t = _SubAgentThread(task, model)
    t.start()
    return t