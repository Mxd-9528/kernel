"""上下文压缩：保留 system + 最近 N 轮，把中间旧对话摘要成结构化文本，替换回历史。

轮次数 assistant（模型一轮可能多步工具调用，数 user 会迟迟不触发）；
摘要作 user/assistant 对回插（不塞 system，避免污染系统约束）。
触发用字符数估算（粗略但够；token 精确但要 tokenizer，YAGNI）。
"""

from call import call

KEEP_ROUNDS = 6       # 保留最近几轮完整对话（数 assistant）
THRESHOLD = 50_000    # 中间可压部分超过多少字符就触发

COMPRESS_PROMPT = """你正在对一个 AI 编程助手的对话历史做结构化压缩。
你的输出会替换对话中较旧的部分，最近几轮完整保留。压缩后模型应能无缝继续工作。

压缩不是降采样式摘要（那会丢核心思想），而是两层并行：
① 事实层——原样照抄，不转述、不诠释、不"优化措辞"；
② 提炼层——在事实之上做受控抽象，把隐含的结构提炼出来。两层分开放，不混。

事实层（原样照抄）：
- 文件路径、文件名
- 错误信息、堆栈跟踪、测试输出、关键执行结果
- 已修改文件的具体变更、关键代码片段

提炼层（基于上述事实，执行三个动作，不脱离事实外推）：
- 析微：把纠缠的问题拆成基本命题，挑明对话里隐含但从未明说的前提与约束
- 取骨：剥离一次性细节，提取"内容会变而结构不变"的内核——这件事的骨架是什么
- 溯源：把分散的踩坑与决策归因到根本前提，而非罗列表面现象

判断什么该留：若不知道某条，后续决策会不会改变？会变就留，不变才删。

严格按此格式输出：

## 已完成
[逐条列出已改的文件、已完成的功能]

## 当前状态
[正在进行的任务及进度]

## 关键事实
[文件路径、错误信息、代码片段、配置变更等，原样照抄]

## 问题骨架
[析微+取骨+溯源的产物：当前问题拆解后的基本命题、不变的结构内核、踩坑与决策的根本原因]

## 避坑
[试过但不通的路、被否定的假设、中途发现的约束——让接续者不重蹈覆辙]

## 待办
[下一步要做的事]"""


def _chars(messages):
    return sum(len(m.get("content", "")) for m in messages)


def split_history(history, keep=KEEP_ROUNDS):
    """拆成 (system, 可压缩中间, 最近keep轮)。轮次数 assistant。不足 keep 轮则中间为空、全保留。"""
    i = 0
    while i < len(history) and history[i]["role"] == "system":
        i += 1
    system, conv = history[:i], history[i:]

    asst = 0
    split = len(conv)
    for j in range(len(conv) - 1, -1, -1):
        if conv[j]["role"] == "assistant":
            asst += 1
            if asst == keep:
                split = j
                break
    if asst < keep:  # 不够 keep 轮，全保留
        return system, [], conv
    # split 落在第 keep 个 assistant 上；往前回退到该轮的 user 起点
    while split > 0 and conv[split - 1]["role"] != "assistant":
        split -= 1
    return system, conv[:split], conv[split:]


def compact(history, keep=KEEP_ROUNDS, threshold=THRESHOLD, model=None):
    """压缩 history：中间部分字符数超 threshold 才压。未达阈值原样返回。
    压缩时摘要中间部分，作 user/assistant 对插回。model 用于调用压缩 LLM。"""
    system, mid, recent = split_history(history, keep)
    if not mid or _chars(mid) <= threshold:
        return history
    summary = compress(mid, model)
    bridge = [
        {"role": "user", "content": "（以下是已压缩的旧上下文摘要）"},
        {"role": "assistant", "content": summary},
    ]
    return system + bridge + recent


def compress(messages, model):
    """把待压消息拼成压缩请求并调用模型，返回摘要文本。提出来独立可测 COMPRESS_PROMPT 拼装。"""
    import json
    req = [
        {"role": "system", "content": COMPRESS_PROMPT},
        {"role": "user", "content": json.dumps(messages, ensure_ascii=False)},
    ]
    return call(req, model)
