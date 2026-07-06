"""工具预置函数测试：read/glob/grep/write/edit/bash/plan/survey/bg_start。"""

import tempfile
import os


def test_read():
    from tools.read import read
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("L1\nL2\nL3\nL4\nL5\n")

        # 全量读：cat -n 行号
        r = read(p)
        assert r == "1\tL1\n2\tL2\n3\tL3\n4\tL4\n5\tL5\n", repr(r)

        # 部分读：offset/limit
        r = read(p, offset=2, limit=2)
        assert r == "2\tL2\n3\tL3\n", repr(r)

        # 文件不存在：raise FileNotFoundError
        try:
            read(os.path.join(d, "nope.txt"))
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("应 raise FileNotFoundError")

        # 目录：raise IsADirectoryError
        try:
            read(d)
        except IsADirectoryError:
            pass
        else:
            raise AssertionError("应 raise IsADirectoryError")

        # 空文件：成功返回空字符串
        e = os.path.join(d, "e.txt")
        open(e, "w").close()
        assert read(e) == ""
    print("read ok")


def test_glob():
    import time
    from tools.glob import glob
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "sub"))
        for name in ("a.py", "sub/b.py", "c.py"):
            p = os.path.join(d, name)
            open(p, "w").close()
            time.sleep(0.01)

        # 自动递归 + mtime 倒序
        r = glob("*.py", d)
        assert isinstance(r, list)
        names = [os.path.basename(p) for p in r]
        assert set(names) == {"a.py", "b.py", "c.py"}, names
        assert names[0] == "c.py" and names[-1] == "a.py", names

        # 无匹配：空列表
        assert glob("*.nope", d) == []

        # 排除噪声：__pycache__ 不出现在结果里
        os.makedirs(os.path.join(d, "__pycache__"))
        open(os.path.join(d, "__pycache__", "x.py"), "w").close()
        r = glob("*", d)
        assert not any("__pycache__" in p for p in r)
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

        # content（默认）：list[dict]，默认排除 __pycache__
        r = grep("import", d)
        assert isinstance(r, list)
        files = {m["file"] for m in r}
        assert any("a.py" in f for f in files) and any("b.txt" in f for f in files)
        assert not any("__pycache__" in f for f in files)

        # files_with_matches：list[str]
        r = grep("import", d, output_mode="files_with_matches")
        assert isinstance(r, list) and all(isinstance(p, str) for p in r)

        # count：dict[str, int]
        r = grep("import", d, output_mode="count")
        assert isinstance(r, dict) and sum(r.values()) == 2

        # 无匹配：空 list
        assert grep("zzzznomatch", d) == []

        # 非法正则：raise re.error
        import re as _re
        try:
            grep("(unclosed", d)
        except _re.error:
            pass
        else:
            raise AssertionError("应 raise re.error")

        # 非法 output_mode：raise ValueError
        try:
            grep("x", d, output_mode="bogus")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError")
    print("grep ok")


def test_write():
    from tools.write import write
    from tools.read import read
    with tempfile.TemporaryDirectory() as d:
        # 基本写入：返回字节数
        p = os.path.join(d, "f.txt")
        n = write(p, "你好\nworld\n")
        assert n == len("你好\nworld\n".encode())
        assert read(p) == "1\t你好\n2\tworld\n"

        # 覆盖已有
        write(p, "new")
        assert "1\tnew" in read(p)

        # 自动建父目录
        deep = os.path.join(d, "a", "b", "c.txt")
        write(deep, "x")
        assert os.path.exists(deep)

        # 写空文件是合法操作，返回 0
        e = os.path.join(d, "empty.txt")
        assert write(e, "") == 0 and os.path.exists(e)
    print("write ok")


def test_edit():
    from tools.edit import edit
    from tools.read import read
    from tools.write import write
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.py")

        # 基本替换：返回 "file:line\ndiff"
        write(p, "import os\nx = 1\nprint(x)\n")
        r = edit(p, "x = 1", "x = 42")
        assert isinstance(r, str)
        assert f"{p}:2" in r
        assert "x = 42" in r and "x = 1" in r  # diff 含 +/- 变更
        assert "x = 42" in read(p)

        # 不匹配：raise ValueError
        write(p, "hello\n")
        try:
            edit(p, "notfound", "y")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError（未匹配）")
        assert read(p) == "1\thello\n"  # 文件未动

        # 多处匹配且未 replace_all：raise ValueError
        write(p, "a\na\na\n")
        try:
            edit(p, "a", "b")
        except ValueError:
            pass
        else:
            raise AssertionError("应 raise ValueError（歧义）")

        # replace_all：全替换
        r = edit(p, "a", "b", replace_all=True)
        assert read(p) == "1\tb\n2\tb\n3\tb\n"

        # 文件不存在：raise FileNotFoundError
        try:
            edit(os.path.join(d, "nope.py"), "a", "b")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("应 raise FileNotFoundError")
    print("edit ok")


def test_bash():
    import subprocess
    from tools.bash import bash

    # 基本执行：返回 CompletedProcess
    r = bash("echo hello")
    assert isinstance(r, subprocess.CompletedProcess)
    assert "hello" in r.stdout
    assert r.returncode == 0

    # 业务失败：命令退出码非零 → returncode 反映，不 raise
    r = bash("exit 3")
    assert r.returncode == 3

    # 硬超时：raise TimeoutExpired（含 output 属性）
    try:
        bash("sleep 5", timeout=1)
    except subprocess.TimeoutExpired as e:
        # 超时前收集的输出附在异常上
        assert hasattr(e, "output")
    else:
        raise AssertionError("应 raise TimeoutExpired")

    # stderr 合并到 stdout（按时序）
    r = bash("echo out; echo err 1>&2")
    assert "out" in r.stdout and "err" in r.stdout
    print("bash ok")


def test_plan():
    from tools.plan import plan

    # 合法三态：格式化整表
    r = plan([
        {"text": "读需求", "status": "completed"},
        {"text": "写代码", "status": "in_progress"},
        {"text": "跑测试", "status": "pending"},
    ])
    assert isinstance(r, str)
    assert "✔ 读需求" in r and "▸ 写代码" in r and "☐ 跑测试" in r

    # 非法 status：raise ValueError
    try:
        plan([{"text": "x", "status": "bogus"}])
    except ValueError:
        pass
    else:
        raise AssertionError("应 raise ValueError")

    # 非 list 输入：raise TypeError
    try:
        plan("not a list")
    except TypeError:
        pass
    else:
        raise AssertionError("应 raise TypeError")

    # 空列表：返回占位字符串
    assert plan([]) == "(计划为空)"
    print("plan ok")


def test_survey():
    """survey 缓存自动管理：首次自动测绘、fingerprint 变化触发重扫、删除文件后模块消失。"""
    import sys
    sys.path.insert(0, "tools")
    import survey as s

    # 1. 首次调用自动测绘
    r = s.survey()
    assert isinstance(r, str) and s._cache
    fp1 = s._cache_fp

    # 2. 未知 mode：raise ValueError
    try:
        s.survey(mode="scan")
    except ValueError:
        pass
    else:
        raise AssertionError("应 raise ValueError（未知 mode）")

    # 3. 新增文件 → 缓存自动失效并包含新模块
    tmp = "__survey_test_tmp.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('"""tmp module."""\ndef hi(): pass\n')
    try:
        s.survey()
        assert "__survey_test_tmp" in s._cache
        assert s._cache_fp != fp1
    finally:
        os.remove(tmp)

    # 4. 删除文件 → 缓存中该模块消失
    s.survey()
    assert "__survey_test_tmp" not in s._cache
    print("survey ok")


def test_bg_start():
    """bg_start 起后台线程，模型可通过 threading.Thread API 查询/等待。"""
    import time
    from tools.bg_start import bg_start

    results = []

    def worker():
        for i in range(3):
            time.sleep(0.05)
            results.append(i)

    t = bg_start(worker)

    # 等待完成
    t.join(timeout=2)
    assert not t.is_alive(), "worker 应已完成"
    assert results == [0, 1, 2]

    # daemon 保证 kernel 退出时清理
    assert t.daemon is True
    print("bg_start ok")


def run_all():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()


if __name__ == "__main__":
    run_all()
    print("工具测试全部通过")
