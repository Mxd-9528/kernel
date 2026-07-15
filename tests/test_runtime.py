"""runtime 模块测试。"""



def test_run_cell():
    from kernel.runtime import _run_cell
    assert _run_cell("1 + 1") == 2
    _run_cell("print('hello')")
    try:
        _run_cell("1/0")
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError("应 raise ZeroDivisionError")
    print("run_cell ok")


def test_extract_blocks():
    from kernel.runtime import extract_blocks
    code = "<EXEC>\n```python\nx = 42\ny = 7\n```\n</EXEC>"
    blocks = extract_blocks(code)
    assert len(blocks) == 1
    assert "y = 7" in blocks[0]
    assert extract_blocks("hello world") == []
    print("extract_blocks ok")


def test_feedback():
    from kernel.runtime import feedback
    # 普通输出
    result = feedback(["hello"])
    assert "[环境反馈]" in result
    assert "hello" in result
    # 异常
    try:
        raise ValueError("bad argument")
    except ValueError as e:
        result = feedback([e])
    assert "ValueError" in result
    assert "bad argument" in result
    # 长输出截断
    long_stdout = "x" * 25000
    result = feedback([long_stdout])
    assert "截断" in result or len(result) < len(long_stdout)
    # 多结果
    result = feedback(["a", "b"])
    assert "代码块 1" in result and "代码块 2" in result
    print("feedback ok")


def test_execute_blocks():
    from kernel.runtime import execute_blocks, extract_blocks
    code = "<EXEC>\n```python\n42\n```\n</EXEC>"
    blocks = extract_blocks(code)
    results = execute_blocks(blocks)
    assert len(results) == 1
    assert results[0] == 42
    print("execute_blocks ok")
