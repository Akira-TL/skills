# 研究计划书与科研 Proposal 写作流程

本文件用于研究计划书、开题报告、基金 / grant proposal、项目申请书中的科研方案部分，以及在已批准项目框架下编写个人或子课题研究计划。它与原始研究论文不同：Proposal 的核心不是报告已经得到的 Results，而是依据当前 evidence 提出**未来要回答的问题、准备如何回答、为什么值得做以及如何判断成败**。

Proposal 属于 Communication，但不能在 Communication 中临时创造 Research Question、Hypothesis、Design 或 Analysis plan。需要新的科学设计时，先返回 `akira-research` 的对应 Skill 建立 canonical scientific state，再回来写。

## 1. 先锁定 Proposal 的真实范围

正式起草前明确：

```text
proposal 类型 / 目标机构
目标读者 / reviewer
当前申请或计划覆盖的研究阶段
用户 / supervisor / funder 已给出的硬约束
篇幅、模板、必填章节与 reporting requirements
哪些工作属于当前作者 / work package
哪些内容明确留到后续阶段
```

如果用户只要求一个阶段、一个子课题或一个初步研究计划，不要为了“看起来完整”自动扩成整个博士课题、整个项目或多年执行书。尚依赖未来设备、样品、合作方、采购或上游 work package 的内容，可以写成后续方向 / dependency / contingency，不应伪装成当前已经可执行的 objective。

若存在已批准的项目本子、funding call、supervisor outline 或机构模板，它们属于**写作约束 / 项目约束 source**，不是发表文献证据。保留其 section / work-package locator，使用其既有术语和职责边界；不要把内部申请书当成 published evidence 引用。

## 2. Proposal 使用 Akira canonical state，不再建立第二套科研 canon

写作前读取与当前 proposal 相关的稳定对象：

- Research Question / Active Uncertainty / Research Tree；
- Literature evidence、supporting / contradictory relations 与 unresolved gap；
- Hypothesis / Prediction / discriminator（若适用）；
- Research Design、sampling、measurement、controls、estimand、stopping / decision rules（已经形成时）；
- preliminary Study / Dataset / Analysis / Observation（若真实存在）；
- feasibility evidence、资源与现实限制；
- 用户、supervisor、funder 或 approved project 的明确约束。

Proposal 可以提出尚未验证的 Hypothesis 和预期结果，但必须与“已经建立的事实”分开。不要复制一份新的 `research_canon` 并让它和 `research.sqlite` / `RESEARCH.md` 竞争 source of truth。

对长篇 proposal，可以维护一个 Communication 派生材料表，至少区分：

| 内容 | 状态 | Canonical source | 可用于什么 |
| --- | --- | --- | --- |
| 已建立事实 | evidence-backed | Paper / Study / Analysis | 背景、可行性、rationale |
| 合理推断 | bounded inference | Interpretation / literature synthesis | rationale，需保留边界 |
| 待检验 Hypothesis | hypothesis | Hypothesis artifact | objectives / predictions |
| 计划动作 | planned | Design / work plan | methods / work packages |
| 未支持主张 | unsupported / unresolved | — | 不直接写成事实；补 evidence 或降级 |

## 3. 先建立 Proposal 的论证，再按模板分章节

Proposal 的基本逻辑通常是：

```text
重要问题 / 当前知识边界
→ 仍未解决的 uncertainty
→ 为什么现有 evidence / method 还不足
→ 本项目准备回答什么
→ 为什么当前 Design 能区分关键解释或减少 uncertainty
→ 如何判断成功、失败和边界
→ 为什么在当前资源与时间内可执行
→ 预期产生什么可检验的科学产出
```

这不是要求所有 Proposal 使用同一章标题。最终章节以 funder / school / supervisor 的正式模板为准。

在写长 prose 前，为每个主要章节先写一个简短的**章节写作约束**：

```text
Purpose：这一节必须让 reviewer 明白什么
Canonical inputs：允许引用哪些项目 / literature source
Allowed claims：当前 evidence 允许写到什么
Forbidden claims：哪些结论尚未建立、不得提前写成事实
Required content：本节必须覆盖的 evidence / design / risk
Exit check：写完后如何判断本节完成
```

章节写作约束只是 Communication 导航，不是新的科研对象；任何 scientific content 仍以 canonical source 为准。

## 4. 科学问题、Objectives 与工作包必须对应

Proposal 不能只有漂亮背景和一串 Methods。至少建立：

```text
Research Question / uncertainty
↔ Objective / Aim
↔ Hypothesis or target decision（若适用）
↔ Work package / Design
↔ measurement / Analysis
↔ success / failure / decision criterion
↔ expected scientific output
```

每个主要 Objective 都应说明为什么需要它、用什么证据回答、什么结果会支持或削弱预期解释。多个 work package 之间如果有依赖，明确前置输入和 fallback；不要把尚未产出的合作方数据当作必然存在。

在已批准大项目内写子课题时，优先保持既有 scientific question、术语、编号和 work-package boundary；可以在执行层细化 measurement、comparison、decision rule 和 independent execution plan，但不要未经用户同意重新定义整个项目立意。

## 5. 文献背景服务于“为什么需要这个 Proposal”

Proposal 的 literature section 不是独立综述，也不是“作者 A 做了什么、作者 B 做了什么”的流水账。围绕当前 Research Question 组织：

```text
已经知道什么
→ 哪些关键 uncertainty / contradiction / capability gap 仍存在
→ 为什么这些 gap 会阻碍目标科学问题
→ 本 Proposal 的 Design 具体减少哪一部分 uncertainty
```

重要 foundation、alternative route 和 contradictory evidence 不能为了凸显创新而删除。如果 literature coverage 不足以支持 gap / novelty 判断，返回 `literature` 补足。

## 6. “创新点”只能写计划贡献，不能提前宣告成功

Innovation / novelty 的对象可以是：

- 新的 Research Question / discriminator；
- 新的 measurement / method capability；
- 新的设计组合或应用范围；
- 对重要矛盾 evidence 的判别；
- 预期建立的新 dataset / resource / benchmark；
- 在已有方法基础上的明确、可验证改进。

但 Proposal 阶段不能把它写成已实现的贡献。优先表达：

```text
本研究拟检验……
本研究将比较……
本设计旨在区分……
若结果满足……，将支持……
```

而不是无证据写：

```text
本研究证明……
本研究建立了……
本方法显著提高……
```

`first / 최초 / 首次 / 唯一 / 从未有人` 等优先性 Claim 继续受 [`audit/CITATION-AUDIT.md`](audit/CITATION-AUDIT.md) 和实际检索边界约束；没有足够 search basis 时使用更窄、可核验的相对贡献表述。

## 7. 可行性不能只写“团队经验丰富”

Feasibility 至少根据当前任务按需覆盖：

- preliminary evidence / pilot data（若真实存在）；
- 已有方法、设备、数据、样品或 access；
- 关键技术是否已有可重建实现或成熟 precedent；
- recruitment / sampling / throughput 是否现实；
- 关键 dependency；
- 最大 failure mode；
- fallback / alternative Design；
- 时间、资源和 work-package interface。

把“我们预计能做成”与“已有 evidence 表明可行”区分开。Simulation / model output、文献 precedent 和本项目 preliminary data 也分别标明，不互相冒充。

## 8. 预期结果、预期产出与风险必须分开

### 预期结果

写成 prediction / expected pattern，并说明它基于什么 Hypothesis / prior evidence。它不是未来事实。

### 预期科学产出

优先写与研究过程直接相关且可交付的对象，例如：

- dataset；
- validated method / assay；
- model / benchmark；
- decision rule；
- quantitative estimate；
- protocol / resource；
- 对一个明确 Research Question 的 evidence。

论文数、专利数、平台指标等若是 funder 必填可以照实写，但不能代替科学 deliverable。

### 风险和替代方案

对决定项目成败的高风险 assumption / dependency，说明：

```text
风险是什么
最早如何发现
什么 observation 表示该路线失败
失败后改走什么 route
alternative route 回答的是不是同一个 scientific question
```

Fallback 不能只是“优化实验条件”；应在可能时给出真正可判别、可执行的替代路径。

## 9. Proposal 的内容先于语言润色

审查顺序优先是：

```text
Scope
→ evidence boundary
→ Research Question / Objectives
→ Design / decision logic
→ feasibility / risks
→ section logic
→ citation / integrity
→ 最后才是 language polishing
```

如果关键 evidence 缺失、Design 尚未成立或两个核心目标互相冲突，不用继续润色掩盖问题；返回对应科研工作流解决，或在 Proposal 中明确 unresolved / contingency。

不使用固定总分阈值来决定 Proposal 是否“科学上通过”。可以按 dimension 给出问题优先级，但一个 central validity / feasibility failure 不能被其他优点平均抵消。

## 10. Proposal revision 与既定框架

如果是在已批准 Proposal / 本子内继续写：

- 先识别哪些 scientific question、Aim、术语、work package 和 KPI 是已批准约束；
- 用户没有授权改变时，不重写立意或把自己的子课题扩成整个项目；
- 需要新增方法时，把它作为支持既定 Aim 的 candidate route，并说明证据和风险；
- 已证明不可行的路线应从核心承诺中删除或降级，不靠更多文字把它包装成仍可交付；
- 对外正式修订仍使用 [`REVISION-WORKFLOW.md`](REVISION-WORKFLOW.md) 的意见—动作—证据规则。

## 11. Proposal 完成检查

至少确认：

1. proposal type、target reader、scope 和当前阶段明确；
2. scientific fact、Hypothesis、planned action、expected result 与 unsupported claim 没有混写；
3. Research Question → Objective → Design → measurement / Analysis → decision criterion 能闭合；
4. literature gap 和 novelty 表述有真实 evidence / search boundary；
5. feasibility 有具体资源、precedent、dependency 和 failure mode，而不是空泛保证；
6. 高风险路线有真实 fallback 或明确停止边界；
7. partial / subproject proposal 没有越界承诺 deferred work 或其他 work package；
8. 每个 major section 的 purpose、canonical inputs、allowed / forbidden claims 已检查；
9. citation、Figure、语言和 integrity 继续遵守 Communication 共用规则；
10. 任何写作中新增的 scientific decision 已先返回 canonical Research state，而不是只存在于 Proposal 草稿。
