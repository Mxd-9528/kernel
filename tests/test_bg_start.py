"""bg_start 工具测试。"""

import time


def test_bg_start():
    from kernel.tools.bg_start import bg_start

    results = []

    def worker():
        for i in range(3):
            time.sleep(0.05)
            results.append(i)

    t = bg_start(worker)

    t.join(timeout=2)
    assert not t.is_alive(), "worker 应已完成"
    assert results == [0, 1, 2]

    assert t.daemon is True
    print("bg_start ok")
