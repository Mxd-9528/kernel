"""chat/main 模块测试。"""


def test_chat_module():
    """chat 模块可导入。"""
    from kernel.chat import chat
    assert callable(chat)
    print("chat_module ok")


def test_main_module():
    """main 模块可导入且有 observer 和 main。"""
    from kernel.main import observer, main
    assert observer is not None
    assert callable(main)
    print("main_module ok")
