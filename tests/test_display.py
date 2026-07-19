"""display 模块测试：_fold_exec_blocks 折叠逻辑。

TerminalRenderer 的行为测试见 test_terminal_renderer.py。
"""


def test_fold_exec_blocks():
    from kernel.display import _fold_exec_blocks
    text = "<EXEC>\n```python\nprint(\'hello\')\n```\n</EXEC>"
    result = _fold_exec_blocks(text)
    assert "<EXEC>" not in result
    assert "hello" in result or "print" in result
    print("fold_exec_blocks ok")
