---
name: ask-akira-research
description: 管理一个可审计、可持续迭代的科研项目；围绕当前 Active Uncertainty 路由文献、假设、设计、数据、分析、解释与写作，而不是按固定线性阶段推进。
disable-model-invocation: true
---

# Ask Akira Research

本 Skill 是 Akira 科研工作的主 Router。科研项目以 Git 仓库承载；`RESEARCH.md` 保存当前研究状态，项目级 `research.sqlite` 保存详细结构化科研知识，原始论文与补充材料作为外部 artifact 保留并由数据库记录身份、路径、版本、来源与获取时间。

## 1. 进入项目

先确认当前目录是否为科研项目，并读取 `RESEARCH.md`。不存在时进入 bootstrap；bootstrap 的最小文件、状态字段与 Git 约定按需读取 [`PROJECT-STATE.md`](PROJECT-STATE.md)。接管已有项目、缺少前序会话上下文、或当前数据库版本可能落后于 Skill 时，同样读取 `PROJECT-STATE.md` 的接管规则：先恢复科学状态和 Git 冻结历史，再把 schema / validator 兼容性作为独立基础设施状态处理，不为让检查通过而自动重做科研工作或改写历史。获得维护授权后如需迁移，按 [`RESEARCH-DB.md`](RESEARCH-DB.md) 的正式 `migrate` 契约执行；迁移对后来新增的语言门禁保留旧文本 Git 基线，但任何迁移后修改的科研文本仍立即适用当前学术语言规范。

完成标准：当前 Objective、Current Loop、唯一 primary Active Uncertainty、Current State 与 Active Work 均已明确，且后续动作可以解释为在降低该 uncertainty。

## 2. 按 Active Uncertainty 路由

`Current Loop` 只表示研究当前主要位于哪里，不规定下一步。允许的定位词为：`EXPLORE`、`QUESTION`、`HYPOTHESIS`、`DESIGN`、`DATA`、`ANALYSIS`、`INTERPRETATION`、`COMMUNICATION`。

每轮先判断当前最阻塞研究的不确定性，再选择信息增益最高且成本合理的下一动作。当前问题混有多个子问题、已有 competing explanations、或需要决定什么 evidence 最能改变当前判断时，读取 [`references/ACTIVE-UNCERTAINTY.md`](references/ACTIVE-UNCERTAINTY.md)；需要把 competing explanations 变成可判别预测时继续读取 [`references/HYPOTHESIS.md`](references/HYPOTHESIS.md)；需要判断哪些新证据、矛盾、猜想或路线分叉应主动呈现给用户，或需要分开记录 Agent 判断、用户主动判断与用户对猜想的明确决策时，读取 [`references/collaboration/RESEARCH-COLLABORATION.md`](references/collaboration/RESEARCH-COLLABORATION.md)；判别 evidence 需要新的 sampling、measurement、control 或 intervention 时读取 [`references/DESIGN.md`](references/DESIGN.md)；需要接收、整理、冻结或追溯项目自身数据时读取 [`references/DATA.md`](references/DATA.md)；需要用冻结数据估计 target contrast、检查 sensitivity 或检验 predictions 时读取 [`references/ANALYSIS.md`](references/ANALYSIS.md)；需要把项目结果与文献 evidence 合并、更新 Claim 层级或重写 Active Uncertainty 时读取 [`references/INTERPRETATION.md`](references/INTERPRETATION.md)；存在论文、报告、摘要、图表、答辩或其他传播目标时读取 [`references/COMMUNICATION.md`](references/COMMUNICATION.md)。需要文献发现、全文获取、论文阅读、批判审阅或跨论文证据综合时，读取 [`LITERATURE.md`](LITERATURE.md)。需要持久化、检索、校验或生成证据视图时，读取 [`RESEARCH-DB.md`](RESEARCH-DB.md)。

不要把科研过程强制推进成单向流水线；文献、假设、实验设计、数据分析和解释可以反复回到彼此。

## 3. 科研语义判断由主模型完成

论文理解、Method / Experiment / Observation / Claim 区分、Critical Audit、证据能否支持某个 Claim、跨论文综合和科研结论都由当前主会话模型直接完成。不要把这些科研语义判断委派给子 Agent、轻量模型或本地小模型。

脚本与其他确定性工具只承担全文获取、文本/文件解析、格式转换、结构校验、事务写入、检索与关系展开；它们不得自行生成或升级科学 Claim、Issue、support relation 或结论。机械性信息摘取可以由工具辅助，但进入科研知识库前必须由主模型核对原文和证据边界。

## 4. 学术术语与科研表述

所有面向用户或进入科研项目的人类可读 scientific prose，包括 `RESEARCH.md`、论文 sidecar、跨论文综合、derived report、论文/摘要/图注草稿，都必须遵守 [`references/standards/ACADEMIC-LANGUAGE.md`](references/standards/ACADEMIC-LANGUAGE.md)。优先使用领域已经存在并可核验的标准学术术语；中文科研写作中重要专业术语首次出现时优先采用“中文标准术语（English standard term）”。对中文译名、英文近义词或领域惯例不确定时，先查同行评议文献或权威术语来源，不凭语言感觉替换。

Agent 不得为了叙事自行创造新词、组合词、效应名、模式名、闭环名或其他命名概念，也不得把内部工作流标签冒充学术概念。尚无固定术语的现象用普通描述性语言表达。确实需要提出新概念时，只能先与用户讨论其必要性、边界和操作性定义；只有用户明确批准名称与定义后，才可进入 canonical scientific prose，并把该决定记录到 `RESEARCH.md` 的 `Key Decisions`。

## 5. 更新研究状态

一次科研动作结束后，只把仍然影响当前路线的高层状态写回 `RESEARCH.md`。详细的论文知识、方法、实验、观察、作者声明、批判问题、检索记录和关系进入 `research.sqlite`；面向人的论文 sidecar 只保留精简核心，不复制数据库。

内部 acquisition / reconstruction / critical bundle 默认放在 `.research/bundles/`，属于 Agent 与数据库脚本之间的内部事务载荷，不放在项目根目录，也不作为科研知识的 canonical source。

用户显式需要完整的人类可读科研评估时，可以额外保存 derived report。它只是原始 artifacts + `research.sqlite` 的派生视图，不形成第四个 canonical source；报告必须指回对应 Paper identity、数据库与原文，任何只存在于报告而没有进入应有 canonical source 的重要 Observation、Claim、Issue 或 evidence boundary 都视为尚未持久化完成。

完成标准：新的 evidence、decision 或 uncertainty 已进入对应 canonical source；`RESEARCH.md` 仍然是短小的 current research map，而不是日志或数据库。

## 6. 审计与提交

科研历史依赖 Git 保存版本演化；结构化数据库内部另保留语义 change log。提交围绕科研事件命名，避免 `update research` 一类无信息提交。

本 Skill 当前处于 `in-progress`。`research-db` 已实现 schema migration、Discovery Search Run / Candidate 队列、Candidate identity reconciliation、论文 acquisition、Pass 1 Reconstruction、Pass 2 Critical Audit、FTS/evidence 检索、跨论文 relation、Discovery closure，以及项目自身 Hypothesis Proposal / User Hypothesis Decision / attributed Research Judgment / Hypothesis Set / Research Design / Dataset / Analysis Run / Analysis Amendment / Project Observation / Hypothesis Evaluation / Communication Product 的最小 provenance 和最终 `validate --completion` 门禁。确认性 Analysis 可以显式连接其已冻结 Research Design，结果后的 Hypothesis Evaluation 作为不可覆盖事件保存证据更新，而不覆盖结果前 freeze 历史；传播产物则记录其 pre-communication source commit 与实际派生 artifact，但仍保持为 canonical scientific evidence 的派生输出。搜索、候选发现、canonical artifact、论文知识单元、项目假设/设计身份、项目数据/分析结果、传播产物、批判问题、关系与 change log 均由同一项目数据库记录必要语义和 pointer；完整 Hypothesis/Design 科研正文、原始论文、数据、代码、结果文件和传播稿仍保持为独立 artifact。Evidence Synthesis 规则见 [`references/RESEARCH-SYNTHESIS.md`](references/RESEARCH-SYNTHESIS.md)。Agent 通过脚本维护数据库，不把直接散写 SQL 作为正常科研工作流。
