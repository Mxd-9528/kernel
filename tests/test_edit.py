"""edit 工具测试。"""

import os
import tempfile


def test_edit():
    from kernel.tools.edit import edit
    from kernel.tools.read import read
    from kernel.tools.write import write
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.py")

        write(p, "import os\nx = 1\nprint(x)\n")
        r = edit(p, "x = 1", "x = 42")
        assert isinstance(r, str)
        assert f"{p}:2" in r
        assert "x = 42" in r and "x = 1" in r
        assert "x = 42" in read(p)

        write(p, "hello\n")
        try:
            edit(p, "notfound", "y")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError（未匹配）")
        assert read(p) == "1\thello\n"

        write(p, "a\na\na\n")
        try:
            edit(p, "a", "b")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError（歧义）")

        r = edit(p, "a", "b", replace_all=True)
        assert read(p) == "1\tb\n2\tb\n3\tb\n"

        try:
            edit(os.path.join(d, "nope.py"), "a", "b")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("应 raise FileNotFoundError")
    print("edit ok")
