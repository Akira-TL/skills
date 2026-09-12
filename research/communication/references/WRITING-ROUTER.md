# 科研写作类型路由

进入 `communication` 后、正式起草长篇 prose 前，先判定**整篇传播产物的主要科学贡献来自哪里**，再选择写作流程。不能因为当前正在写 Introduction、文献回顾段落或某一节分析，就改变整篇文稿类型。

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

这些类型的检索、筛选、数据提取、质量评价和综合本身属于科研方法。若相应 canonical research workflow 尚未完成，应退出 Communication，返回 `akira-research`，按当前权威方法学与 reporting guideline 建立并完成相应 Design / Literature / Data / Analysis / Interpretation provenance，形成稳定 source commit 后再进入 Communication。不得用普通叙述性综述的写作方式冒充正式系统综述、范围综述或荟萃分析的方法学过程。

完成上游研究后，Communication 只负责把已经完成的方法、结果和综合准确写成论文。

### 1.4 其他传播产物

摘要、poster、presentation、reviewer response、protocol document、项目报告等根据实际目的使用 [`CONTRACT.md`](CONTRACT.md) 与 [`WRITING-EXPRESSION.md`](WRITING-EXPRESSION.md)。若其中包含完整原始研究论文或综述主体，再按其主要科学贡献加载对应 workflow。

## 2. 判定依据不是章节名称，而是主要科学贡献

优先回答：

> 如果删除本项目新产生的数据和分析，这篇稿件的核心学术贡献是否仍然成立？

- 若否，主要贡献依赖本项目新结果，通常属于原始研究论文；
- 若是，而且主要价值来自对已有文献的重新组织、比较和综合，通常属于普通综述；
- 若其主要贡献来自预先定义且可复现的检索、筛选、评价与统计综合，则属于系统综述、范围综述或荟萃分析等正式证据综合研究。

以下现象不能单独决定类型：

- 原始研究论文有很长的 Introduction / literature review；
- 普通综述包含 evidence table、概念图、时间线或 bibliometric summary；
- thesis 同时包含综述章节和原创研究章节；
- report 同时引用既有文献和本项目分析结果。

对混合型 thesis / report，按每个可独立成篇的主要部分分别选择 workflow；整篇总稿再做统一的 communication provenance 与语言审查。

## 3. 无法判定时先澄清，不得默认套原始研究流程

若从用户目标、项目状态、publication target 和现有 canonical evidence 无法可靠判断文稿类型，而且不同类型会实质改变检索、结构或方法要求，则在开始长篇 prose 前先澄清传播目标。不得因为 `RESEARCH-ARTICLE-WORKFLOW.md` 已存在，就把所有 manuscript 默认写成原始研究论文。

## 4. 共同底线

不论选择哪条写作流程，都继续遵守：

- [`CONTRACT.md`](CONTRACT.md) 的 canonical source、Claim traceability、citation、evidence boundary 与 communication provenance；
- [`WRITING-EXPRESSION.md`](WRITING-EXPRESSION.md) 的大/小逻辑表达、连接词与结论强度约束；
- 当前适用的 reporting guideline 与学术语言规范。

类型路由只决定**怎样组织和起草**，不改变科学证据本身。
