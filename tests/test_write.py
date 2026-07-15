"""write 工具测试。"""

import os
import tempfile


def test_write():
    from kernel.tools.write import write
    from kernel.tools.read import read
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.txt")
        n = write(p, "你好\nworld\n")
        assert n == len("你好\nworld\n".encode())
        assert read(p) == "1\t你好\n2\tworld\n"

        write(p, "new")
        assert "1\tnew" in read(p)

        deep = os.path.join(d, "a", "b", "c.txt")
        write(deep, "x")
        assert os.path.exists(deep)

        e = os.path.join(d, "empty.txt")
        assert write(e, "") == 0 and os.path.exists(e)
    print("write ok")
