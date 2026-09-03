---
name: research-tree
description: 维护科研项目的分支研究结构与跨对象关系；当研究问题产生子问题、竞争假设、替代解释、独立分析路线或需要在多个科研分支之间选择当前推进路径时使用。
---

# Research Tree

`research-tree` 管理科研项目的**研究结构**，不替代 `akira-research` 的单节点科研判断，也不替代具体分析执行。树回答“研究从哪里分叉、当前推进哪一支、各科研对象如何互相连接”。

## 1. 读取当前树

进入已有项目时先恢复 Root Objective、当前 active path、open / blocked / resolved branches，以及与当前分支直接相关的跨节点关系。没有树时，从当前 `RESEARCH.md` 的 Objective 与 primary Active Uncertainty 建立最小 Root 和当前节点，不把历史内容机械拆成大量节点。

节点与关系模型按需读取 [`references/MODEL.md`](references/MODEL.md)。

完成标准：能明确回答当前节点是什么、为什么从父节点产生、它连接哪些关键科研对象、下一条研究动作属于哪一支。

## 2. 只在科学分叉时创建节点

一个新节点必须对应可独立讨论、验证、分析或关闭的科研内容，例如：

- 新的 Question / Objective；
- competing Hypothesis 或替代解释；
- 为回答某个问题而形成的独立 Design / Analysis；
- 能改变上游判断的重要 Observation / Claim；
- 新发现的 boundary condition、数据质量问题或方法学不确定性。

参数微调、重复运行、格式变化和纯实现步骤保持为同一 Analysis 的 provenance，不为了版本管理制造科研节点。

创建节点时记录 `spawned_from`：说明它由哪个节点、哪条 evidence 或哪次讨论产生，以及为什么值得独立推进。

## 3. 树与图同时维护

每个节点只有一条主要结构父边，用于形成可读的研究树；科研对象之间另外允许横向语义关系，因此完整结构是“主树 + 关系图”。

关系只表达实际科学语义，不用关系名代替解释。首版关系词保持小集合：

- `spawned_from`：研究分叉来源；
- `addresses`：某对象直接回答一个 Question；
- `supports` / `weakens` / `contradicts`：evidence 对 Hypothesis / Claim 的方向；
- `alternative_to`：竞争解释或替代路线；
- `depends_on`：当前对象依赖另一对象成立或完成；
- `uses`：Analysis / Design 使用 Dataset、Method 或其他输入；
- `produces`：Analysis / Literature / Design 产生 Observation、Claim 或新 Question。

需要更精确关系时先使用已有 `akira-research` / literature relation；只有现有语义无法表达且该关系会影响科研推理时才扩展树关系集合。

## 4. 选择 active path

树可以同时存在多个 open branch，但一次科研推进只选择当前信息增益最高的一条 active path。`akira-research` 在该节点内部维护 primary Active Uncertainty，并决定 Literature、Hypothesis、Design、Data、Analysis、Interpretation 或 Communication 动作。

当前节点完成一次科研动作后：

1. 把新的 evidence / decision / relation 连接回树；
2. 判断当前节点是继续、部分解决、阻塞还是可以关闭；
3. 若结果产生新的独立科学问题，创建子节点；
4. 比较所有可执行 open branch 的信息增益，选择新的 active path；
5. 回到 `akira-research` 继续实际科研。

不要按创建时间、节点编号或“版本更高”选择分支。

## 5. 分支收敛

节点的 lifecycle 只表示研究工作状态：`open`、`active`、`blocked`、`resolved`、`closed`。Hypothesis 的 favored / weakened / contradicted 等科学状态继续由 `akira-research` 的 Hypothesis Evaluation 表达，不与节点 lifecycle 混用。

关闭节点前必须留下最窄结论、仍成立的边界和对子/父节点的影响。父节点根据子节点结果重新解释，而不是把最后运行的分析自动当作“最终版本”。

## 6. Artifact 与 Git 边界

树保存科研语义和 pointer，不要求所有 artifact 进入 Git。大型数据、模型、中间矩阵、大量图片或可重建结果可以保留在项目外部或 Git 忽略目录；代码、配置、manifest、关键科研文本和需要冻结的计划继续按 `akira-research` provenance 规则进入 Git。

外部 artifact 的身份、位置、来源、版本、producer、input 与所属节点必须可追溯。具体规则按需读取 [`references/ARTIFACTS.md`](references/ARTIFACTS.md)。

当前 Skill 第一版只定义行为契约；在经过黑盒验证前，不为树对象强行扩展 `research.sqlite` schema。稳定后再把 Node / Edge / artifact pointer 下沉为结构化 provenance。
