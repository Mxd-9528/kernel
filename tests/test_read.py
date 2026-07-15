"""read 工具测试。"""

import tempfile
import os


def test_read():
    from kernel.tools.read import read
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("L1\nL2\nL3\nL4\nL5\n")

        r = read(p)
        assert r == "1\tL1\n2\tL2\n3\tL3\n4\tL4\n5\tL5\n", repr(r)

        r = read(p, offset=2, limit=2)
        assert r == "2\tL2\n3\tL3\n", repr(r)

        try:
            read(os.path.join(d, "nope.txt"))
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("应 raise FileNotFoundError")

        try:
            read(d)
        except IsADirectoryError:
            pass
        else:
            raise AssertionError("应 raise IsADirectoryError")

        e = os.path.join(d, "e.txt")
        open(e, "w").close()
        assert read(e) == ""
    print("read ok")
