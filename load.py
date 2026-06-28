
# 把机件摆上 IPython 命名空间。预置函数（tools/）由 manifest 扫描、inject 注入，不在这里手写。
# 注入判断标准：只有模型在执行任务时真的会直接调用的东西才放进来
from call import call
from extract import extract
from result import Result, ListResult, DictResult
from run import run
from agent import agent
from chat import chat
from system_prompt import build as build_system_prompt
from manifest import list_tools
from skills import list_skills