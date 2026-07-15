"""history 模块测试。"""

import tempfile
import os


def test_history_save_load():
    from kernel.history import save, load, reset_history

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "h.json")

        assert load(p) is None

        msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
        save(msgs, p)
        assert load(p) == msgs

        with open(p, "w", encoding="utf-8") as f:
            f.write("{坏 json")
        assert load(p) is None

    test_msgs = [{"role": "system", "content": "test save"}]
    save(test_msgs)
    result = load()
    assert isinstance(result, list)
    assert result[0]["content"] == "test save"

    initial = reset_history()
    assert isinstance(initial, list)
    assert initial[0]["role"] == "system"
    print("history_save_load ok")


def test_history_observer():
    from kernel.observer import BaseObserver
    from kernel.history import observer
    assert isinstance(observer, BaseObserver)
    required = {"on_thinking", "on_delta", "on_flush", "before_send", "save", "display_msg"}
    methods = {m for m in dir(observer) if not m.startswith("_") and callable(getattr(observer, m))}
    missing = required - methods
    assert not missing, f"history.observer 缺少方法: {missing}"
    print("history_observer ok")
