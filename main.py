'''入口：加载所有模块，启动对话。'''
import llm      # 注册 @on("send")
import compact  # 注册 @on("before_send")
import runtime  # 注册 @on("execute")
import commands # 注册 @on("on_command")
from chat import chat

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model)
