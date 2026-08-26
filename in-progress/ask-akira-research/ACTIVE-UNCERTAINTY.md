# Active Uncertainty Contract

Active Uncertainty 是当前科研路线的控制变量：它不是“还有哪些问题”，而是**当前哪一个未知最值得被下一条证据改变**。详细历史与证据留在 `research.sqlite` 和 Git；`RESEARCH.md` 只保留当前 primary uncertainty 的紧凑状态。

## 1. 选择 primary uncertainty

从 Evidence Synthesis 的 `unresolved` 与 `Most Discriminating Next Evidence` 出发，选择一个满足以下条件的问题：

- **单一**：可以由同一类 evidence / analysis / experiment 实质推进；若不同子问题需要不同下一动作，拆开并把非 primary 项移入 `Open Threads`。
- **可判别**：至少存在两个当前证据尚不能区分的 plausible explanations / states；仅仅“我们还不知道更多细节”不是充分理由。
- **决策相关**：不同答案会改变后续研究路线、解释或设计；即使解决也不会改变任何动作的问题不应成为 primary。
- **可行动**：能够指出现实可获得的下一条 discriminating evidence；若当前没有任何可行信息增益，记录为 Open Thread，而不是占据 primary。

优先级由预期信息增益、对 Objective 的影响和取得证据的现实成本共同决定，不用固定数值评分代替科研判断。

## 2. 在 `RESEARCH.md` 中的最小表达

`## Active Uncertainty` 保持为短小 current state，推荐结构：

```text
Question: <一个可以独立回答的问题>

Competing explanations:
- <E1>
- <E2>

Discriminating gap: <为什么当前证据区分不了 E1/E2>

Best next evidence: <最能改变当前判断的一条 observation / analysis / experiment>
```

只有在第三个 explanation 会导向不同可检验预测时才保留；不要为了“全面”枚举大量几乎等价的解释。

`Active Work` 记录当前实际执行的动作及其与 `Best next evidence` 的关系，避免把工作计划塞回 uncertainty 本身。

## 3. Competing explanations

Competing explanations 是当前问题的替代解释模型，还不是必须持久化成独立 Hypothesis 实体。每个 explanation 至少应满足：

- 与当前已知 evidence 相容到尚未被排除的程度；
- 与至少另一个 explanation 对某个可观测结果给出不同预测；
- 不把“没有效应”“共同原因”“反向因果”“测量/选择偏差”默认排除在候选之外。

若两个 explanation 对所有现实可测结果都没有不同预测，它们在当前阶段不可判别，应合并或把分歧降为 Open Thread。

## 4. Discriminating evidence

`Best next evidence` 描述的是**什么结果最能区分 competing explanations**，不是默认指定某种研究阶段。它可以来自：

- 已有数据的重新分析；
- 新的文献证据；
- 额外 metadata / measurement；
- observational follow-up；
- perturbation / intervention；
- replication；
- 新实验设计。

选择下一动作时先检查已有项目数据或已入库证据是否足够取得该 evidence；可以直接分析时不应为了流程完整性先设计新实验。

## 5. 更新与退出

一次科研动作结束后重新判断 competing explanations：

- 新 evidence 明显区分了解释 → 更新 `Current State`，关闭或重写当前 uncertainty；
- 新 evidence 只缩小范围 → 保留问题但更新 gap / explanations / next evidence；
- 发现更基础的 confounder 或 measurement problem → 允许把 primary uncertainty 上移到该阻塞点；
- evidence 对当前问题没有信息增益 → 不把“做过一次分析/实验”误记成 uncertainty 已降低。

任何时刻 `RESEARCH.md` 只保留一个 primary Active Uncertainty；被替换但仍重要的问题进入 `Open Threads`，其演化历史由 Git 保存。

## 6. 何时进入 Hypothesis / Design

当 primary uncertainty 已有至少两个可判别 explanations，且需要明确它们的预测才能决定下一证据时，进入 `HYPOTHESIS`。当判别所需 evidence 需要新的 sampling、measurement、control 或 intervention 时再进入 `DESIGN`。

因此 `HYPOTHESIS` 与 `DESIGN` 是降低 uncertainty 的工具，不是必经阶段。
