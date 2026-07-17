"""Agent 子代理测试。"""


def test_agent_tool():
    """tools.agent 后台执行，通过 .result() 获取结果。"""
    from kernel.tools.agent import agent as agent_tool

    f = agent_tool("回复 hello，只回复这一个词，不要多余内容")
    result = f.result(timeout=30)
    assert isinstance(result, str)
    assert "hello" in result.lower()
    print("agent_tool ok")


def test_agent_core():
    """kernel.agent 同步执行，返回消息列表。"""
    from kernel.agent import agent as agent_core

    messages = agent_core("回复 hello 只回复这一个词", model="openai/gpt-4o-mini")
    assert isinstance(messages, list)
    assert len(messages) > 0
    print("agent_core ok")
