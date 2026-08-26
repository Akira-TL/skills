# Research State

`RESEARCH.md` 是科研项目当前状态的 canonical source。它回答“这个项目现在在研究什么、卡在哪里、正在做什么”，不保存详细历史、论文抽取结果或数据库内容。

## Bootstrap

新的科研项目首先确认 Git 仓库；若当前目录尚不是 Git repository，则初始化 Git。Bootstrap 只强制创建 `RESEARCH.md`，其他目录和文件按真实需求出现，不预生成空的 `literature/`、`hypotheses/`、`analysis/` 等目录。初始化 Git 不等于完成 provenance：最迟在第一个可独立解释的科研状态形成时必须提交一次，不能让整个科研项目长期停留在“有 `.git` 但没有任何 commit”的状态。

最小结构：

```markdown
# Research

## Objective

## Current Loop

## Active Uncertainty

## Current State

## Active Work

## Open Threads

## Key Decisions

## References
```

## 字段语义

- `Objective`：当前研究试图理解、解释或解决什么；尚未形成具体问题时允许保持宽泛。
- `Current Loop`：只用于定位当前主要研究区域，取 `EXPLORE`、`QUESTION`、`HYPOTHESIS`、`DESIGN`、`DATA`、`ANALYSIS`、`INTERPRETATION`、`COMMUNICATION` 之一；它不规定下一步。
- `Active Uncertainty`：当前最值得解决、且真实阻塞研究推进的一项 primary uncertainty。它必须能作为一个独立问题被回答；其选择、competing explanations、discriminating gap 与 next evidence 按 [`references/ACTIVE-UNCERTAINTY.md`](references/ACTIVE-UNCERTAINTY.md) 执行。若多个问题需要不同下一动作，只保留信息增益最高的一个，其余移入 `Open Threads`。
- `Current State`：让新的 Agent 在较短文本内理解“目前已经知道什么、还不知道什么”的 current synthesis。
- `Active Work`：现在正在做什么，以及它为什么能降低 Active Uncertainty；与 uncertainty 本身分开记录。
- `Open Threads`：已经发现但当前不追的其他问题，避免研究被每个新线索带走。
- `Key Decisions`：仍然影响当前路线的有效决定；旧版本由 Git history 保存，不把演化日志堆进正文。
- `References`：只保存指向详细 artifacts、数据库视图或其他研究资产的 pointer。

## 路由原则

每轮研究先读取 Active Uncertainty，再选择最合适的动作。示例：

- 不知道领域中哪些现象稳定、哪些问题 unresolved → 文献发现。
- 已有 competing explanations，但证据不足以区分 → 文献、分析或新实验设计中选择信息增益最高者。
- 现有数据足以直接检验 → 分析。
- 观察结果无法区分 confounder 与 mechanism → hypothesis / design。

不要把“当前在文献阶段”当成继续搜索的充分理由。

## 更新边界

一次科研动作结束后，只把仍然影响当前路线的内容写回 `RESEARCH.md`：新的 Active Uncertainty、Current State、Active Work、Open Threads、仍然有效的 Key Decisions，以及必要 pointer。

详细文献知识、检索历史、方法、实验、观察、声明、批判问题和关系进入项目级 SQLite；原始 PDF 与 supplement 保持为独立 artifact。Git 负责保存 `RESEARCH.md` 与数据库的版本演化，因此不额外维护重复的 research log。每个可独立解释的科研事件完成后提交本轮 owned changes；用户已有、与本轮无关的工作区修改不触碰、不暂存、不重置。

当 Agent 准备向用户声明“本轮科研项目已完成”时，必须先提交本轮拥有的 canonical research artifacts 和本轮生成的 derived outputs，然后运行 `research-db validate --completion`。普通 `research-db validate` 只证明 SQLite/科研知识库内部一致，不证明 Git provenance 已完成；`--completion` 额外要求科研项目本身是独立 Git repository、已经存在 commit、canonical research artifacts 已被 Git 跟踪且当前没有未提交修改，并在存在 Literature Discovery 时检查 Candidate 队列是否闭合。任何一项失败都不得宣称项目完成。

## Git 语义

科研提交应表达发生了什么研究事件，例如：

```text
RESEARCH: establish initial evidence landscape
LITERATURE: identify conflicting altitude definitions
HYPOTHESIS: add diet-confounding alternative
DESIGN: separate group assignment from sequencing batch
ANALYSIS: weaken altitude association after diet adjustment
INTERPRETATION: reclassify pathway Y as exploratory
```

这些是研究项目自身未来采用的语义示例，不替代当前 Akira Skills 仓库的全局 Git 提交格式。
