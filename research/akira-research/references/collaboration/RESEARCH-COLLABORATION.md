# 科研协作与判断来源记录

本文件定义主模型如何在科研过程中主动筛选需要呈现给用户的信息，并把 Agent 判断、用户主动判断与用户对猜想的明确决策分别保存。这里的 Hypothesis Proposal、Research Judgment、User Hypothesis Decision 是项目内部 provenance 对象，不是新的学术概念。

## 1. Agent 默认承担的判断

Agent 不把日常科研整理机械转交给用户。以下工作通常自行完成并持久化到对应 canonical source：

- 检索结果去重、明显噪声排除与全文阅读排序；
- 常规 Method / Experiment / Observation / Claim 抽取；
- 不改变当前科研路线的重复证据与次要 limitation；
- competing explanations 的初步生成、合并与淘汰；
- 判断下一条 evidence 来自继续检索、已有数据分析还是新 Design。

这些动作只有在产生会改变项目判断的新信息时才需要在用户回复中重点呈现，不能把数据库流水账当作科研协作。

## 2. Agent 应主动呈现给用户的信息

当本轮工作出现下列任一情况时，Agent 应主动把它提升到用户可见层，而不是只写入数据库：

- 新 evidence 实质改变当前 scientific interpretation 或 Active Uncertainty；
- 出现可信 contradiction、negative result、boundary condition 或 previously untested alternative；
- 某篇工作即使结论本身不可靠，但对领域主流叙事、关键方法、反例或后续设计具有用户需要知道的价值；
- competing explanations 的集合发生实质变化；
- 出现一条明显比继续普通检索更有判别力的 observation / analysis / experiment；
- 下一步存在科学价值、资源成本或论文战略明显不同的路线分叉。

Agent 应说明“为什么这条信息值得用户看”，而不是只给论文列表。可以明确区分：直接科学证据价值、研究路线决策价值、方法借鉴价值、反证价值、领域叙事价值，以及“需要知道但不应据此采信结论”的工作。

## 3. 三类来源必须分开

### 3.1 假设提案（Hypothesis Proposal）

任何可能进入 Active Uncertainty、Hypothesis Set、后续检索路线或 Design 的科学猜想，若值得持续追踪，使用 `research-db record-hypothesis-proposal` 保存来源。

必须保留：

- `origin=user|agent`：最初是谁提出；
- `original_statement`：最初的科学语义；用户提出时尽量保留其原始表述，不只保存 Agent 改写；
- `operationalized_statement` / `operationalized_by`：若后来由用户或 Agent 转化为可检验表述，可以在同一 proposal 上**一次性追加**，不覆盖 origin / original statement；已有操作化表述不得再重写；
- Agent-origin proposal 必须有 `rationale`，说明当前 evidence 或项目状态为什么仍允许该解释。

Proposal 的来源字段不可覆盖。允许的后续变化仅是第一次补入可检验操作化；猜想的科学语义实质改变时建立新的 proposal，而不是修改旧来源历史。

### 3.2 用户对猜想的决策（User Hypothesis Decision）

用户明确表达“值得探索、优先、暂缓、拒绝、修改”时，使用 `research-db record-user-hypothesis-decision` 追加事件，并把用户实际表达保存在 `source_statement`，不能只留下 Agent 概括：

- `accepted_for_exploration`
- `prioritized`
- `deferred`
- `rejected`
- `modified`

用户接受 Agent proposal 后，proposal 的 `origin` 仍然是 `agent`。没有明确用户表达时，不生成同意事件；**absence of a decision is not consent**。`decision=modified` 表示用户改变了科学猜想本身，此时必须先建立新的 Hypothesis Proposal，并通过 `resulting_proposal_slug` 指向它；其他 decision 不得借该字段静默创造新猜想。

“同意探索”表示研究方向或资源选择，不表示该 hypothesis 得到 scientific evidence 支持。科学证据状态仍由 Hypothesis artifact 中的 `live/favored/weakened/ruled_out_within_scope` 与结果后的 Hypothesis Evaluation 决定。

### 3.3 科研判断（Research Judgment）

影响科研路线但不等同于 Hypothesis 的判断，使用 `research-db record-research-judgment` 按 actor 分开记录。每一条记录只能属于一个来源：`actor=user|agent`。

适用类型：

- `scientific_assessment`：对当前 evidence boundary 的判断；
- `research_priority`：优先研究哪个问题或方向；
- `strategic_preference`：机制、预测、验证、论文定位等科研战略选择；
- `resource_constraint`：样本、平台、时间、伦理、访问权限等现实约束；
- `recommendation`：Agent 基于证据与信息增益给出的下一步建议。

Agent judgment 必须保存 `basis`；用户 judgment 必须保存 `source_statement`，避免历史只剩 Agent 的概括。Agent 与用户判断可以不同；不得为了形成统一叙事而覆盖其中任何一方。

## 4. 何时需要用户参与

不要因为 Agent 生成了多个 competing explanations 就逐个请求批准。普通探索性 proposal 可以先记录并继续低成本检索。

当某个判断将发生以下任一变化时，应主动把关键分叉呈现给用户：

- 改变项目 Objective 或主要科学问题；
- 替换唯一 primary Active Uncertainty，且不同选择会形成实质不同的科研路线；
- 进入需要明显新资源的 sampling、measurement、control 或 intervention；
- 某个 proposal 将成为正式 Design、确认性冻结或论文核心叙事的主要依据；
- 存在证据无法替代的价值判断，例如机制深挖与预测性能之间的战略取舍。

如果用户已经明确授权 Agent 在某个范围内自主选择路线，可以在该授权范围内继续，不重复请求逐项批准；应把这一授权作为用户的 `strategic_preference` 或 `research_priority` 保存。不得把广泛授权伪造成用户对每个具体 proposal 的科学赞同。

## 5. 与 Hypothesis Set 的关系

schema v18 起新建的 Hypothesis Set 必须通过 `proposal_slugs` 指回至少一个已记录的 Hypothesis Proposal。该 link 表示这些 proposal 参与形成了正式 hypothesis set，不把 proposal 的来源、用户决策或科学状态合并进 Hypothesis Set 生命周期字段。

因此四个问题始终分别回答：

1. **谁提出的？** → Hypothesis Proposal `origin`；
2. **用户后来怎么处理？** → User Hypothesis Decision history；
3. **Agent 与用户各自如何判断路线？** → attributed Research Judgment；
4. **证据目前支持到什么程度？** → evidence synthesis、Hypothesis artifact 与 Hypothesis Evaluation。

迁移到 schema v18 之前已经存在的 Hypothesis Set 不追溯补造 proposal provenance；旧历史保持原样。迁移后新建的集合必须满足新规则。

## 6. 每轮科研协作的完成条件

当一次科研动作真正改变了项目状态时，结束前检查：

- 新的重要 evidence / contradiction / route change 已主动呈现给用户；
- 值得持续追踪的新猜想已有正确 `origin`；
- 用户主动提出的科学判断没有被改写成 Agent judgment；
- 用户明确接受/拒绝/优先某个 proposal 时已有独立 decision event；
- Agent recommendation 与用户选择不一致时两者均保留；
- “用户同意探索”没有被写成 scientific support；
- 正式 Hypothesis Set 能追溯到其 proposal 来源。
