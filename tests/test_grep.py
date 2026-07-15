"""grep 工具测试。"""

import os
import tempfile
import re as _re


def test_grep():
    from kernel.tools.grep import grep
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.py"), "w", encoding="utf-8") as f:
            f.write("import os\ndef foo():\n    return OS_ERR\n")
        with open(os.path.join(d, "b.txt"), "w", encoding="utf-8") as f:
            f.write("hello\nimport sys\n")
        os.makedirs(os.path.join(d, "__pycache__"))
        with open(os.path.join(d, "__pycache__", "junk.py"), "w", encoding="utf-8") as f:
            f.write("import noise\n")

        r = grep("import", d)
        assert isinstance(r, list)
        files = {m["file"] for m in r}
        assert any("a.py" in f for f in files) and any("b.txt" in f for f in files)
        assert not any("__pycache__" in f for f in files)

        r = grep("import", d, output_mode="files_with_matches")
        assert isinstance(r, list) and all(isinstance(p, str) for p in r)

        r = grep("import", d, output_mode="count")
        assert isinstance(r, dict) and sum(r.values()) == 2

        assert grep("zzzznomatch", d) == []

        try:
            grep("(unclosed", d)
        except _re.error:
            pass
        else:
            raise AssertionError("应 raise re.error")

        try:
            grep("x", d, output_mode="bogus")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError")
    print("grep ok")
