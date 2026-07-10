'''入口：加载所有模块，启动对话。'''
import compact  # 注册 @on("before_send")
import display  # 注册 @on("display_delta") @on("display")
import history  # 注册 @on("save")
from chat import chat

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else None
    chat(model=model)
