---
name: akira-research
description: 统一管理可审计、可持续迭代的科研项目；根据 Research Question、当前 evidence、research-tree 与适用科研规范，路由 literature、hypothesis、design、study、data、analysis、interpretation 与 communication，而不是按固定线性阶段推进。
disable-model-invocation: true
---

# Akira Research

`akira-research` 是科研系列 Skills 的总 Router。它管理项目级 Scientific Objective、当前科研状态、research-tree、适用规范、子 Skill 路由与停止边界；具体文献、假设、设计、实施、数据、分析、解释和传播规则由对应子 Skill 负责。

科研项目以 Git repository 承载；`RESEARCH.md` 保存短小的当前科研状态，`.research/research.sqlite` 保存已有结构化科研 provenance 与知识对象，原始论文、Dataset、代码、模型、图片等仍作为独立 artifact 保存并通过 pointer / provenance 关联。

## 1. 进入或接管项目

先读取 `RESEARCH.md`；不存在时按 [`PROJECT-STATE.md`](PROJECT-STATE.md) bootstrap。接管已有项目时同时运行 `research-db status`，用数据库对象、canonical artifacts 与 Git history 恢复 Objective、Active Uncertainty、冻结点、结果边界、当前分支和下一条真实工作。

数据库 schema / validator 兼容性是基础设施状态，不等于科学状态。需要迁移时按 [`RESEARCH-DB.md`](RESEARCH-DB.md) 的正式契约处理，不为了让 validator 通过而重写历史科研事实。

完成标准：能够说明当前 Objective、primary Research Question / Active Uncertainty、Current Loop、Current State、Active Work、主要 open branches 与已有 blocker。

## 2. 先确定科研问题、分支与适用规范

Research Question、Active Uncertainty、分支和跨对象关系由 [`research-tree`](../research-tree/SKILL.md) 管理。多个独立问题同时存在时，明确 primary active branch；其他分支保持 open / blocked / resolved 状态，不压回一个线性版本序列。

当研究类型、研究实施、metadata、provenance、统计方法或报告要求会影响当前动作时，调用 [`research-standards`](../research-standards/SKILL.md) 从当前权威来源核验适用规范。Akira 只负责采用和编排已有规范，不把内部 workflow 当作新的科研方法论；reporting guideline、design guidance、metadata standard、provenance standard、方法学依据和软件文档必须按各自职责使用。

## 3. 路由到专业 Skill

`Current Loop` 只用于定位当前主要研究区域，可取：`EXPLORE`、`QUESTION`、`HYPOTHESIS`、`DESIGN`、`STUDY`、`DATA`、`ANALYSIS`、`INTERPRETATION`、`COMMUNICATION`。它不规定下一步。

每轮根据当前 primary branch 选择信息增益最高、当前可执行且最可能改变核心科学判断的动作：

- 不知道已有研究、关键方法、矛盾或边界条件 → [`literature`](../literature/SKILL.md)；
- 存在真正 competing explanations，需要结果前 prediction / discriminator → [`hypothesis`](../hypothesis/SKILL.md)；
- 需要新的 estimand、sampling、comparison、measurement、controls 或 protocol → [`design`](../design/SKILL.md)；
- frozen Design 已进入真实采样、实验、观察或 Assay 实施，需要记录实际执行与 deviation → [`study`](../study/SKILL.md)；
- 已有 raw / external data，需要 identity、metadata、QC、curation、sample mapping 或 freeze → [`data`](../data/SKILL.md)；
- 已有可分析 Dataset，需要统计、生物信息、Python、R、机器学习、sensitivity 或 exploratory computation → [`analysis`](../analysis/SKILL.md)；
- 已有 Observation / result，需要与 Design、Hypothesis 和 literature evidence 综合并形成最窄 Claim → [`interpretation`](../interpretation/SKILL.md)；
- 已有稳定 scientific state 且存在真实论文、报告、图表、答辩或其他传播目标 → [`communication`](../communication/SKILL.md)。

不是所有研究都必须经过所有 Skill。探索性研究可以没有 formal Hypothesis；公开数据研究可以没有本项目自己的 Study；已有证据足以回答问题时也不机械进入 Design。

需要判断 Agent proposal、用户主动判断或用户对科学猜想的决定来源时，读取 [`references/collaboration/RESEARCH-COLLABORATION.md`](references/collaboration/RESEARCH-COLLABORATION.md)。

## 4. 子 Skill 返回后重新路由

任一子 Skill 完成当前有边界动作后：

1. 持久化本轮新增的 scientific objects、evidence relations、decision、artifact pointers 与 provenance；
2. 把新的 Question / Hypothesis / Design / Study / Analysis / Observation / Claim 及其关系接回 `research-tree`；
3. 更新当前 branch 的 open / active / blocked / resolved / closed 状态；
4. 重新读取 `RESEARCH.md` 与刚形成的 canonical evidence；
5. 重新比较所有当前可执行分支，选择新的 primary active branch 与下一 Skill，并实际继续执行。

子 Skill 可以提供 next-action candidate，但最终路由权属于 `akira-research`。不得因为某个子工作流 `COMPLETED`、Current Loop 已切换、一次 validation 通过或已经生成阶段总结就自动结束整个科研任务。

正式路由到完整 `literature` 工作流后，遵守其自身 `COMPLETED / BLOCKED` 契约；Candidate 队列、全文、Critical Audit 或 discovery closure 未完成时继续该工作流，而不是把阶段进度当作最终完成。

## 5. 连续科研循环与停止边界

广义的“继续科研”“接管并继续”“从零完整研究”等请求默认持续执行上述循环。只有出现以下边界之一才停止：

- 用户明确限定的科研范围已经完成；
- Objective 或当前科学问题已经在现有 evidence boundary 内得到足够回答，剩余 uncertainty 不再改变核心结论；
- 下一条真正有判别力的 evidence 必须依赖当前项目不存在的新样本、新实验、新测量、伦理/机构批准、权限、凭据或其他外部现实输入，而且等待前仍可由 Agent 完成的研究工作已完成；
- 存在当前 Agent 无法自行解除、必须等待用户或外部条件的真实 blocker。

如果 `Active Work` 仍指向当前环境下可以实际执行的研究动作，则广义科研任务尚未到达停止边界。

## 6. 科研判断、术语与证据边界

论文理解、Method / Study / Observation / Claim 区分、Critical Audit、evidence-to-claim fit、Hypothesis 更新和科学结论都由当前主会话模型直接判断。脚本和确定性工具负责获取、解析、结构校验、事务写入、检索与关系展开，不自行升级 scientific Claim。

所有面向用户或进入科研项目的人类可读 scientific prose 遵守 [`references/standards/ACADEMIC-LANGUAGE.md`](references/standards/ACADEMIC-LANGUAGE.md)。优先使用已有标准学术术语；重要专业术语首次出现采用规范中文与 established English term / acronym 的对应方式。没有现成术语时用描述性语言，不把 Akira 内部标签包装成学术概念；真正需要提出新概念时先与用户讨论并获得明确批准。

## 7. 项目状态与 provenance

`RESEARCH.md` 只保存仍影响路线的 Objective、Current Loop、Active Uncertainty、Current State、Active Work、Open Threads、Key Decisions 与重要 pointers，不变成日志或数据库 dump。

详细 paper knowledge、Hypothesis/Design provenance、Dataset、Analysis、Observation、Evaluation、Communication Product 等继续使用项目 `research.sqlite` 的已有结构化能力；数据库尚未覆盖的新 Study / research-tree 语义先用 canonical artifact + Git +明确 pointer 保存，不用散写 SQL 临时创造非正式 schema。

大型 Dataset、模型、中间矩阵和大量图片不因 provenance 要求而强制进入 Git。代码、配置、计划、manifest、关键科研文本和需要冻结的对象按其 Skill 契约进入 Git；外部 artifact 使用稳定 identity、version、location、producer、input 和所属研究对象保持可追溯。

## 8. 审计与提交

科研历史依赖 Git 保存版本演化，结构化数据库另保留其语义 change log。每个可独立解释的科研事件按全局原子提交规则收口。

准备声明一个有边界科研工作流或里程碑完成前，先提交本轮 owned canonical artifacts / derived outputs，再运行 `research-db validate --completion`。该门禁证明当前已实现的 provenance / workflow 条件闭合，不证明 Scientific Objective 已被“验证为真”。

完成标准：项目状态、research-tree、适用规范、子工作流结果、provenance 与 Git history 彼此一致，且总 Router 能解释为什么下一步继续、切换分支或在真实边界停止。
