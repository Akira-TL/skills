# 科研写作类型路由

进入 `communication` 后、正式起草长篇 prose 前，先判定**整篇传播产物是在报告既有研究、综合既有文献，还是提出未来研究计划**，再选择写作流程。不能因为当前正在写 Introduction、文献回顾段落或某一节分析，就改变整篇文稿类型。

## 1. 先判定整篇文稿类型

### 1.1 原始研究论文

若主要科学贡献来自本项目新产生的 Study、Dataset、Analysis、Observation、Experiment 或 Interpretation，例如实验研究、观察性研究、计算方法研究、组学研究等，按 [`RESEARCH-ARTICLE-WORKFLOW.md`](RESEARCH-ARTICLE-WORKFLOW.md) 写作。

其默认逻辑是：

```text
完整材料盘点
→ 主要结论
→ Results
→ Discussion
→ 反推 Introduction
→ Methods
→ Abstract / Title
→ Supplement / Appendix
```

原始研究论文的 Introduction 即使包含大量 literature review，整篇仍然属于原始研究论文，不因此切换到综述流程。

### 1.2 叙述性文献综述 / 普通综述

若主要科学贡献来自**对既有文献的组织、比较、批判、综合和概念性整合**，而不是本项目新产生的实验或主要数据结果，按 [`REVIEW-WORKFLOW.md`](REVIEW-WORKFLOW.md) 写作。

普通综述不能套用“先主要结论 → Results → Discussion”的原始研究流程，也不应为了模仿研究论文而人为制造 Results / Discussion 章节。其正文应围绕 Review Question、Scope、主题分类、跨论文综合、理论/概念框架、争议、研究缺口与未来方向组织。

### 1.3 系统综述、范围综述与荟萃分析

若传播目标明确声明为系统综述（Systematic Review）、范围综述（Scoping Review）、荟萃分析（Meta-analysis），或者研究目的本身要求可复现检索、正式纳入排除标准、筛选流程、质量/偏倚评价、数据提取或定量证据综合，则**不能直接按普通综述开始写作**。

这些类型的检索、筛选、数据提取、质量评价和综合本身属于科研方法。若相应 canonical research workflow 尚未完成，应退出 Communication，返回 `akira-research`：先由 `design` 冻结 Review protocol，再按 [`literature` 的 SYSTEMATIC workflow](../../literature/references/SYSTEMATIC-REVIEW.md) 完成 protocol-bound search、deduplication、screening、全文 eligibility、extraction 与适用的 study-level appraisal；需要结构化 / 定量综合时把 extraction 提升为 canonical Dataset，并由 `analysis` 执行 Meta-analysis 或其他正式统计综合，最后由 `interpretation` 形成 evidence boundary。形成稳定 source commit 后再进入 Communication。不得用普通叙述性综述的写作方式冒充正式系统综述、范围综述或荟萃分析的方法学过程。

完成上游研究后，Communication 只负责把已经完成的方法、结果和综合准确写成论文。

### 1.4 研究计划书、开题与 Grant Proposal

若文稿的核心任务是说明**未来准备回答什么科学问题、为什么值得做、准备如何做、如何判断成败和为什么可行**，而不是报告已经完成的 Results，按 [`PROPOSAL-WORKFLOW.md`](PROPOSAL-WORKFLOW.md) 写作。

这包括研究计划书、开题报告、基金 / grant proposal、项目申请中的科研方案部分，以及在已批准项目框架内编写个人 / 子课题研究计划。Proposal 可以使用已有 preliminary data，但这些数据只承担 rationale / feasibility / preliminary evidence；不能因为有 preliminary result 就把整篇文稿误判为原始研究论文。

Proposal 写作不授权 Communication 临时创造 Design。若 Research Question、Hypothesis、sampling、measurement、comparison、Analysis plan 或 decision rule 尚未形成而它们会改变科学含义，先返回 `akira-research` 对应流程建立 canonical state，再回来起草。

### 1.5 其他传播产物

摘要、poster、presentation、reviewer response、protocol document、项目报告等根据实际目的使用 [`CONTRACT.md`](CONTRACT.md) 与 [`WRITING-EXPRESSION.md`](WRITING-EXPRESSION.md)。若其中包含完整原始研究论文、综述或 Proposal 主体，再加载对应 workflow。

## 2. 判定依据不是章节名称，而是主要科学贡献

优先回答：

> 这篇文稿是在**报告已经获得的 scientific result**、**综合已有文献形成新的领域理解**，还是**提出未来要执行的研究计划**？

- 主要贡献依赖本项目已经产生的新 Study / Data / Analysis / Observation → 通常属于原始研究论文；
- 主要价值来自既有文献的组织、比较和综合 → 通常属于普通综述；
- 主要贡献来自预先定义且可复现的检索、筛选、评价与统计综合 → 属于系统综述、范围综述或荟萃分析等正式证据综合研究；
- 主要目的在于争取批准 / 资源或明确未来研究路线，正文核心是 Question、Aim、Design、feasibility、risk 和 expected output → 属于 Proposal。

以下现象不能单独决定类型：

- 原始研究论文有很长的 Introduction / literature review；
- 普通综述包含 evidence table、概念图、时间线或 bibliometric summary；
- thesis 同时包含综述章节和原创研究章节；
- report 同时引用既有文献和本项目分析结果。

对混合型 thesis / report，按每个可独立成篇的主要部分分别选择 workflow；整篇总稿再做统一的 communication provenance 与语言审查。

## 3. 无法判定时先澄清，不得默认套原始研究流程

若从用户目标、项目状态、publication target 和现有 canonical evidence 无法可靠判断文稿类型，而且不同类型会实质改变检索、结构或方法要求，则在开始长篇 prose 前先澄清传播目标。不得因为 `RESEARCH-ARTICLE-WORKFLOW.md` 已存在，就把所有 manuscript 默认写成原始研究论文。

## 4. 文稿类型确定后，再处理学科与 Venue

本文件只解决“这是什么文稿”。完成类型路由后，再按 [`context/DISCIPLINE-VENUE.md`](context/DISCIPLINE-VENUE.md) 判断目标 discipline / audience / venue 的表达与审查惯例，并让 `research-standards` 核验当前官方要求。不要把“原始研究 vs 综述 vs Proposal”和“生物医学 vs ML vs 人文社科”“期刊 A vs 会议 B”混成同一维度。

## 5. 共同底线

不论选择哪条写作流程，都继续遵守：

- [`CONTRACT.md`](CONTRACT.md) 的 canonical source、Claim traceability、citation、evidence boundary 与 communication provenance；
- [`WRITING-EXPRESSION.md`](WRITING-EXPRESSION.md) 的大/小逻辑表达、连接词与结论强度约束；
- 当前适用的 reporting guideline 与学术语言规范。

类型路由只决定**怎样组织和起草**，不改变科学证据本身。
