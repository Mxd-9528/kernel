"""glob 工具测试。"""

import os
import time
import tempfile


def test_glob():
    from kernel.tools.glob import glob
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "sub"))
        for name in ("a.py", "sub/b.py", "c.py"):
            p = os.path.join(d, name)
            open(p, "w").close()
            time.sleep(0.01)

        r = glob("*.py", d)
        assert isinstance(r, list)
        names = [os.path.basename(p) for p in r]
        assert set(names) == {"a.py", "b.py", "c.py"}, names
        assert names[0] == "c.py" and names[-1] == "a.py", names

        assert glob("*.nope", d) == []

        os.makedirs(os.path.join(d, "__pycache__"))
        open(os.path.join(d, "__pycache__", "x.py"), "w").close()
        r = glob("*", d)
        assert not any("__pycache__" in p for p in r)
    print("glob ok")
