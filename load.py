
# 把机件摆上 IPython 命名空间。预置函数（tools/）由 manifest 扫描、inject 注入，不在这里手写。
from call_contract import call  # 沉淀线：读 call_contract.py 即知全部对外行为
import background_contract  # 沉淀线：后台任务合同（run_with_timeout / task_status / task_cancel）
from extract import extract
from result import Result, ListResult, DictResult
from run import run
from agent import agent
from chat import chat
from compact import compact, should_compact
from system_prompt import build as build_system_prompt
from manifest import list_tools
from skills import list_skills
from history import save as save_history, load as load_history