---
name: ask-akira-research
description: 管理一个可审计、可持续迭代的科研项目；围绕当前 Active Uncertainty 路由文献、假设、设计、数据、分析、解释与写作，而不是按固定线性阶段推进。
disable-model-invocation: true
---

# Ask Akira Research

本 Skill 是 Akira 科研工作的主 Router。科研项目以 Git 仓库承载；`RESEARCH.md` 保存当前研究状态，项目级 `research.sqlite` 保存详细结构化科研知识，原始论文与补充材料作为外部 artifact 保留并由数据库记录身份、路径、版本、来源与获取时间。

## 1. 进入项目

先确认当前目录是否为科研项目，并读取 `RESEARCH.md`。不存在时进入 bootstrap；bootstrap 的最小文件、状态字段与 Git 约定按需读取 [`PROJECT-STATE.md`](PROJECT-STATE.md)。

完成标准：当前 Objective、Current Loop、唯一 primary Active Uncertainty、Current State 与 Active Work 均已明确，且后续动作可以解释为在降低该 uncertainty。

## 2. 按 Active Uncertainty 路由

`Current Loop` 只表示研究当前主要位于哪里，不规定下一步。允许的定位词为：`EXPLORE`、`QUESTION`、`HYPOTHESIS`、`DESIGN`、`DATA`、`ANALYSIS`、`INTERPRETATION`、`COMMUNICATION`。

每轮先判断当前最阻塞研究的不确定性，再选择信息增益最高且成本合理的下一动作。需要文献发现、全文获取、论文阅读、批判审阅或跨论文证据综合时，读取 [`LITERATURE.md`](LITERATURE.md)。需要持久化、检索、校验或生成证据视图时，读取 [`RESEARCH-DB.md`](RESEARCH-DB.md)。

不要把科研过程强制推进成单向流水线；文献、假设、实验设计、数据分析和解释可以反复回到彼此。

## 3. 科研语义判断由主模型完成

论文理解、Method / Experiment / Observation / Claim 区分、Critical Audit、证据能否支持某个 Claim、跨论文综合和科研结论都由当前主会话模型直接完成。不要把这些科研语义判断委派给子 Agent、轻量模型或本地小模型。

脚本与其他确定性工具只承担全文获取、文本/文件解析、格式转换、结构校验、事务写入、检索与关系展开；它们不得自行生成或升级科学 Claim、Issue、support relation 或结论。机械性信息摘取可以由工具辅助，但进入科研知识库前必须由主模型核对原文和证据边界。

## 4. 更新研究状态

一次科研动作结束后，只把仍然影响当前路线的高层状态写回 `RESEARCH.md`。详细的论文知识、方法、实验、观察、作者声明、批判问题、检索记录和关系进入 `research.sqlite`；面向人的论文 sidecar 只保留精简核心，不复制数据库。

内部 acquisition / reconstruction / critical bundle 默认放在 `.research/bundles/`，属于 Agent 与数据库脚本之间的内部事务载荷，不放在项目根目录，也不作为科研知识的 canonical source。

完成标准：新的 evidence、decision 或 uncertainty 已进入对应 canonical source；`RESEARCH.md` 仍然是短小的 current research map，而不是日志或数据库。

## 5. 审计与提交

科研历史依赖 Git 保存版本演化；结构化数据库内部另保留语义 change log。提交围绕科研事件命名，避免 `update research` 一类无信息提交。

本 Skill 当前处于 `in-progress`。`research-db` 已实现 schema migration、`init`、`migrate`、`ingest-paper`、`ingest-reading`、`ingest-critical`、`status` 与 `validate`；论文获取、Pass 1 Reconstruction 和 Pass 2 Critical Audit 都通过原子 bundle 写入，并把 canonical artifact、知识单元、批判问题、关系与 change log 保存在同一项目数据库中。FTS 检索和 evidence 查询仍按 [`RESEARCH-DB.md`](RESEARCH-DB.md) 继续实现。Agent 通过脚本维护数据库，不把直接散写 SQL 作为正常科研工作流。
