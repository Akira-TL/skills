---
name: research-tree
description: 维护科研项目的 Research Question、Active Uncertainty、研究分支与跨对象科学关系；当新问题、新假设、新观察或新分析路线产生分叉，或需要在多个开放分支之间选择当前推进路径时使用。
---

# Research Tree

`research-tree` 管科研进程与科学推理关系。`akira-research` 是总 Router；本 Skill 不决定具体文献、设计、实验、数据或统计方法，只回答“当前在研究什么、为什么产生这个分支、哪些对象互相支持/限制、下一条 active branch 是哪一支”。

## 1. 恢复当前研究结构

进入项目时恢复 Root Objective、当前 Research Question / Active Uncertainty、active path、open / blocked / resolved branches，以及与当前分支直接相关的科学关系。没有树时，只从现有 `RESEARCH.md` 和 canonical research artifacts 建立最小结构，不机械把历史文件全部转成节点。

Research Question 与 Active Uncertainty 的写法按需读取 [`references/ACTIVE-UNCERTAINTY.md`](references/ACTIVE-UNCERTAINTY.md)；对象与关系模型见 [`references/MODEL.md`](references/MODEL.md)。若用户只有宽泛主题、现象描述或模糊 Idea，尚不足以形成可判别问题，先按 [`references/IDEA-FRAMING.md`](references/IDEA-FRAMING.md) 用最少的 decision-relevant 追问与必要 Literature Discovery 收敛问题；不要直接把宽泛主题润色成 Research Question，也不要用大问卷替代科研判断。

完成标准：能明确回答当前问题是什么、它从哪里产生、哪些已有证据或研究对象与它直接相关、哪些其他分支仍开放。

## 2. 只有科学分叉才创建节点

新节点必须对应可独立研究、判别、解释或关闭的科学内容，例如：

- 新 Research Question；
- competing Hypothesis；
- 独立 Study Design / Study；
- 回答不同科学问题的 Analysis；
- 能改变上游判断的重要 Observation / Claim。

参数微调、重复运行、软件兼容修复、文件格式变化和纯实现步骤属于 provenance，不自动产生科研节点。合理的 sensitivity analysis 是否成为独立 Analysis 节点，由它是否回答独立科学问题决定，而不是由运行次数决定。Git 中同样保持这一区分：**commit / Analysis Attempt 表示同一路线的一次可重放执行状态，branch 只表示真实科研路线分叉**。完整命名、merge、归档和禁止历史重写规则见 [`references/GIT-BRANCHES.md`](references/GIT-BRANCHES.md)。

## 3. 主树与科学关系同时维护

每个节点保留一条主要结构父边，形成容易阅读的研究进程树；科学对象之间可以存在横向关系，因此底层允许形成图。

关系优先复用已有科研语义；常见关系包括：

- `spawned_from`：新问题/对象由什么产生；
- `addresses`：对象直接回答哪个 Question；
- `tests`：Design / Analysis 检验哪个 Hypothesis 或 discriminator；
- `supports` / `weakens` / `contradicts` / `qualifies`：Observation 或已有 evidence 对 Hypothesis / Claim 的影响；
- `alternative_to`：竞争解释或替代路线；
- `depends_on`：当前对象依赖另一对象；
- `uses` / `produces`：Activity 与输入/输出的研究关系。

Evidence 默认表现为“有来源依据的科学关系”，不为了结构对称额外制造 Evidence Node。每条会改变科学判断的关系必须能指回 Observation、论文、分析结果或其他 canonical basis。

## 4. 选择 active branch

允许多个 open branch 同时存在；项目始终明确一个 primary active branch，必要时其他分支可以并行工作。选择依据是：

- 对 Root Objective 的影响；
- 预期信息增益；
- 当前是否可执行；
- 是否可能改变主要 Claim 或研究路线；
- 用户明确的科研优先级。

不用节点创建顺序、编号或所谓“最新版本”决定优先级。

每次子 Skill 返回新结果后：

1. 把新对象和科学关系接回树；
2. 更新当前节点的开放/解决/阻塞状态；
3. 若产生新的独立问题，创建新分支；
4. 比较当前可执行分支并更新 active path；
5. 把控制权交回 `akira-research` 继续路由。

## 5. 状态与科学判断分开

节点 workflow state 只表示工作状态，例如 `open`、`active`、`blocked`、`resolved`、`closed`。Hypothesis 的 `favored`、`weakened`、`ruled_out_within_scope` 等属于科学状态，由 `hypothesis` / `interpretation` 根据 evidence 更新，不和 workflow state 混用。

关闭分支时保留最窄结论、适用范围、剩余 uncertainty、`closure_reason` 和对父节点的影响。旧分支不因被替代而从研究历史消失。未 merge 的 Git 科研路线使用 `research-closed/<kind>/<slug>` annotated archival tag 固定 branch tip；已接受路线使用保留拓扑的普通 merge 进入 `main`。

## 6. Artifact 与 provenance

树保存科研语义和 pointer，不要求大型 Dataset、模型、中间矩阵或图片进入 Git。Research Node、Edge、root/active path 与已登记 Research branch provenance 进入项目 `research.sqlite`；数据库契约由 [`akira-research/RESEARCH-DB.md`](../akira-research/RESEARCH-DB.md) 统一维护。Git branch 名不承担 workflow state：`main` 是当前接受的 canonical research state，开放科研路线使用 `research/<kind>/<slug>`。文件、数据、代码、模型等 provenance 仍由 `study` / `data` / `analysis` 按项目约束记录；树只连接它们与对应科研对象。需要外部 artifact 边界时读取 [`references/ARTIFACTS.md`](references/ARTIFACTS.md)。

完成标准：新的科学分叉、关系、状态和 active path 已可恢复，且总 Router 能据此选择下一条实际科研动作。
