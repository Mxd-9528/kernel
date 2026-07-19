"""chat/main 模块测试。"""


def test_chat_module():
    """chat 模块可导入。"""
    from kernel.chat import chat
    assert callable(chat)
    print("chat_module ok")


def test_main_module():
    """main 模块可导入且有 main 入口。"""
    from kernel.main import main
    assert callable(main)
    print("main_module ok")
