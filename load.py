
# 把机件摆上 IPython 命名空间。预置函数（tools/）由 manifest 扫描、inject 注入，不在这里手写。
# 面向接口编程：一律 import 无前缀的接口模块（call/background/compact/run），实现在 _*.py 水线以下。
from call import call
import background
from extract import extract
from result import Result, ListResult, DictResult
from run import run
from agent import agent, build_system as build_system_prompt
from chat import chat
from compact import compact
from manifest import list_tools
from skills import list_skills
from history import save as save_history, load as load_history
