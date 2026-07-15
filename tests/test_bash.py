"""bash 工具测试。"""

import subprocess


def test_bash():
    from kernel.tools.bash import bash

    r = bash("echo hello")
    assert isinstance(r, subprocess.CompletedProcess)
    assert "hello" in r.stdout
    assert r.returncode == 0

    r = bash("exit 3")
    assert r.returncode == 3

    try:
        bash("sleep 5", timeout=1)
    except subprocess.TimeoutExpired as e:
        assert hasattr(e, "output")
    else:
        raise AssertionError("应 raise TimeoutExpired")

    r = bash("echo out; echo err 1>&2")
    assert "out" in r.stdout and "err" in r.stdout
    print("bash ok")
