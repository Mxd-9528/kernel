"""工具预置函数测试：read/glob/grep/write/edit/bash/survey。"""

import tempfile
import os


def test_read():
    from tools.read import read
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("L1\nL2\nL3\nL4\nL5\n")

        # 全量读：cat -n 行号、facts 完整、error=None
        r = read(p)
        assert r.error is None
        assert r == "1\tL1\n2\tL2\n3\tL3\n4\tL4\n5\tL5\n", repr(str(r))
        assert r.lines == 5 and r.line_start == 1 and r.line_end == 5

        # 部分读：offset/limit
        r = read(p, offset=2, limit=2)
        assert r == "2\tL2\n3\tL3\n", repr(str(r))
        assert r.lines == 2 and r.line_start == 2 and r.line_end == 3

        # 文件不存在：error 承载异常，不抛
        r = read(os.path.join(d, "nope.txt"))
        assert isinstance(r.error, FileNotFoundError) and r.lines == 0

        # 目录：分类为 IsADirectoryError
        r = read(d)
        assert isinstance(r.error, IsADirectoryError)

        # 空文件：成功，0 行
        e = os.path.join(d, "e.txt")
        open(e, "w").close()
        r = read(e)
        assert r.error is None and r.lines == 0 and r == ""

        # 大文件：read 无行数上限；超大内容由 Result 层字符截断兜底。
        big = os.path.join(d, "big.txt")
        with open(big, "w", encoding="utf-8") as f:
            f.write("".join(f"line{i}\n" for i in range(3000)))
        r = read(big)
        assert r.error is None and r.lines == 3000
        assert str(r).endswith("3000\tline2999\n")
    print("read ok")


def test_glob():
    import time
    from tools.glob import glob
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "sub"))
        # 按需要的 mtime 顺序建文件：a.py 最旧，c.py 最新
        for name in ("a.py", "sub/b.py", "c.py"):
            p = os.path.join(d, name)
            open(p, "w").close()
            time.sleep(0.01)

        # 自动递归 + mtime 倒序
        r = glob("*.py", d)
        names = [os.path.basename(p) for p in r]
        assert set(names) == {"a.py", "b.py", "c.py"}, names
        assert r.error is None and r.count == 3
        assert names[0] == "c.py" and names[-1] == "a.py", names

        # 无匹配：空列表，error=None（不是失败）
        r3 = glob("*.nope", d)
        assert list(r3) == [] and r3.error is None and r3.count == 0

        # 排除噪声：__pycache__ 目录不出现在结果里
        os.makedirs(os.path.join(d, "__pycache__"))
        open(os.path.join(d, "__pycache__", "x.py"), "w").close()
        r4 = glob("*", d)
        assert not any("__pycache__" in p for p in r4), "应排除 __pycache__ 目录"
    print("glob ok")


def test_grep():
    from tools.grep import grep
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.py"), "w", encoding="utf-8") as f:
            f.write("import os\ndef foo():\n    return OS_ERR\n")
        with open(os.path.join(d, "b.txt"), "w", encoding="utf-8") as f:
            f.write("hello\nimport sys\n")
        os.makedirs(os.path.join(d, "__pycache__"))
        with open(os.path.join(d, "__pycache__", "junk.py"), "w", encoding="utf-8") as f:
            f.write("import noise\n")

        # content（默认）：含文件、行号、文本；默认排除 __pycache__
        r = grep("import", d)
        files = {m["file"] for m in r}
        assert any("a.py" in f for f in files) and any("b.txt" in f for f in files)
        assert not any("__pycache__" in f for f in files), "应默认排除噪声目录"
        assert r.error is None and r.lines_matched == 2

        # files_with_matches：路径列表
        r = grep("import", d, output_mode="files_with_matches")
        assert isinstance(list(r), list) and any("a.py" in p for p in r)

        # count：{文件: 匹配数}
        r = grep("import", d, output_mode="count")
        assert isinstance(r, dict) and sum(r.values()) == 2

        # 无匹配：空，error=None
        r = grep("zzzznomatch", d)
        assert list(r) == [] and r.error is None

        # 非法正则：error 承载，不抛
        r = grep("(unclosed", d)
        assert r.error is not None

        # 非法 output_mode：error 承载
        r = grep("x", d, output_mode="bogus")
        assert r.error is not None
    print("grep ok")


def test_write():
    from tools.write import write
    from tools.read import read
    with tempfile.TemporaryDirectory() as d:
        # 基本写入：返回 path，facts 带 bytes，error=None
        p = os.path.join(d, "f.txt")
        r = write(p, "你好\nworld\n")
        assert r.error is None and p in str(r)
        assert r.bytes == len("你好\nworld\n".encode())
        assert read(p) == "1\t你好\n2\tworld\n"

        # 覆盖已有
        write(p, "new")
        assert "1\tnew" in read(p)

        # 自动建父目录
        deep = os.path.join(d, "a", "b", "c.txt")
        r = write(deep, "x")
        assert r.error is None and os.path.exists(deep)

        # 写空文件是合法操作（touch），不报错
        e = os.path.join(d, "empty.txt")
        r = write(e, "")
        assert r.error is None and os.path.exists(e) and r.bytes == 0
    print("write ok")


def test_edit():
    from tools.edit import edit
    from tools.read import read
    from tools.write import write
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.py")

        # 基本替换：返回 file:line，facts 带 diff，文件真改了
        write(p, "import os\nx = 1\nprint(x)\n")
        r = edit(p, "x = 1", "x = 42")
        assert r.error is None
        assert r.line == 2
        assert "x = 42" in r.diff and "x = 1" in r.diff
        assert "x = 42" in read(p)

        # 不匹配：error 承载，文件不动
        write(p, "hello\n")
        r = edit(p, "notfound", "y")
        assert r.error is not None and read(p) == "1\thello\n"

        # 多处匹配且未 replace_all：报歧义错，不动文件
        write(p, "a\na\na\n")
        r = edit(p, "a", "b")
        assert r.error is not None

        # replace_all：全替换
        r = edit(p, "a", "b", replace_all=True)
        assert r.error is None and read(p) == "1\tb\n2\tb\n3\tb\n"

        # 文件不存在：error
        r = edit(os.path.join(d, "nope.py"), "a", "b")
        assert isinstance(r.error, FileNotFoundError)
    print("edit ok")


def test_bash():
    from tools.bash import bash

    # 基本执行：stdout 进 Body，returncode=0，工具自身 error=None
    r = bash("echo hello")
    assert r.error is None and "hello" in str(r) and r.returncode == 0

    # 业务失败：命令退出码非0 → returncode 进 facts，但工具 error 仍是 None
    r = bash("exit 3")
    assert r.error is None and r.returncode == 3

    # 超时：error 承载 TimeoutExpired，不挂起
    r = bash("sleep 5", timeout=1)
    assert isinstance(r.error, __import__("subprocess").TimeoutExpired)
    print("bash ok")


def test_survey():
    """survey 缓存自动管理：首次自动测绘、fingerprint 变化触发重扫、删除文件后模块消失。"""
    import sys
    sys.path.insert(0, "tools")
    import survey as s

    # 1. 首次调用自动测绘
    r = s.survey()
    assert r.error is None and s._cache, "首次 overview 未自动测绘"
    fp1 = s._cache_fp

    # 2. 未知 mode（含 scan）报错
    assert s.survey(mode="scan").error is not None, "scan 应已移除"

    # 3. 新增文件 → 缓存自动失效并包含新模块
    tmp = "__survey_test_tmp.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('"""tmp module."""\ndef hi(): pass\n')
    try:
        s.survey()
        assert "__survey_test_tmp" in s._cache, "新增文件后应重扫"
        assert s._cache_fp != fp1
    finally:
        os.remove(tmp)

    # 4. 删除文件 → 缓存中该模块消失
    s.survey()
    assert "__survey_test_tmp" not in s._cache, "删除文件后模块应从缓存消失"
    print("survey ok")


def run_all():
    test_read()
    test_glob()
    test_grep()
    test_write()
    test_edit()
    test_bash()
    test_survey()


if __name__ == "__main__":
    run_all()
    print("工具测试全部通过")
