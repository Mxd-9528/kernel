"""plan 工具测试。"""


def test_plan():
    from kernel.tools.plan import plan

    r = plan([
        {"text": "read", "status": "completed"},
        {"text": "write", "status": "in_progress"},
        {"text": "test", "status": "pending"},
    ])
    assert isinstance(r, str)
    assert "read" in r and "write" in r and "test" in r

    try:
        plan([{"text": "x", "status": "bogus"}])
    except ValueError:
        pass
    else:
        raise AssertionError("应 raise ValueError")

    try:
        plan("not a list")
    except TypeError:
        pass
    else:
        raise AssertionError("应 raise TypeError")

    assert plan([]) == "(计划为空)"
    print("plan ok")
