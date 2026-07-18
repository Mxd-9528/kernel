# AutoGPT 项目索引（由 kernel 会话生成）

## 规模
- 1535 Python 文件 / 1776 TypeScript 文件 / 总 65.5 MB
- 1319 模块进入 ast 索引（跳过测试/迁移）
- 4110 条内部 import 依赖

## 顶层布局
- `autogpt_platform/` — 新平台（backend Python + frontend Next.js）**主战场**
- `classic/` — 旧版 AutoGPT（forge / original_autogpt）
- `docs/` — 文档
- 22 份 AGENTS.md / CLAUDE.md 分布在各子目录，**AI 导航优先读**

## 核心模块（按被依赖次数排序 = 事实上的项目支柱）
| 被依赖 | 模块 | 推断的角色 |
|---|---|---|
| 277 | backend.data.model | 数据契约 / Schema 单一事实源 |
| 177 | backend.blocks._base | Block 插件基类（相当于本项目 tools/） |
| 115 | backend.util.exceptions | 统一异常层级 |
| 113 | backend.util.settings | 配置 |
| 108 | backend.copilot.model | Copilot 领域模型 |
| 104 | backend.sdk | SDK 门面 |
| 91 | backend.integrations.providers | 外部集成 |
| 84 | backend.data.execution | 执行数据模型 |

## 移植候选模式（学习优先级）
1. **AGENTS.md 分层导航** — 每个子系统自带 AI 阅读入口（22 份）
2. **Block 基类 + 注册** — 对比本项目 tools/ 的"约定扫描"路线
3. **backend.data.model** — 被 277 处依赖仍稳定，深模块活体样本
4. **集中 exceptions 模块** — 是否值得引入待定，本项目宪法主张"用标准异常"

## 阅读路径（切片顺序）
1. `AGENTS.md`（3.8K，顶层）
2. `autogpt_platform/AGENTS.md`（5.5K）
3. `autogpt_platform/backend/AGENTS.md`（10K，最详细）
4. `autogpt_platform/backend/backend/blocks/_base.py`（Block 基类）
5. 随机抽 1-2 个 block 具体实现，看 Block 契约怎么落地
6. `backend/data/model.py`（277 次被依赖的核心）

## 关联文件
- `modules.json` — 1319 模块的类/函数签名（1.15 MB，供 grep/查询）
- `imports.json` — 依赖边（供图分析）
