"""bg_start 工具测试。"""

import time


def test_bg_start():
    from kernel.tools.bg_start import bg_start

    results = []

    def worker():
        for i in range(3):
            time.sleep(0.05)
            results.append(i)

    f = bg_start(worker)

    f.result(timeout=2)
    assert f.done(), "worker 应已完成"
    assert results == [0, 1, 2]

    print("bg_start ok")
