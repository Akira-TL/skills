---
name: communication
description: 把已经建立的 scientific state、方法、证据边界与 provenance 转成原始研究论文、文献综述、报告、摘要、图表、补充材料、答辩或 reviewer response；当存在真实传播目标时使用。
---

# Communication

`communication` 负责科学表达，不负责创造新的科学结论。进入本 Skill 前，关键 Observation、Claim、Design / Study / Analysis 边界应已在 canonical research state 中稳定。

## 1. 先判定传播类型，再确认适用规范

明确产物类型、受众与用途后，**正式起草长篇 prose 前先按 [`references/WRITING-ROUTER.md`](references/WRITING-ROUTER.md) 判定整篇文稿的主要科学贡献属于原始研究论文、普通文献综述，还是系统综述 / 范围综述 / 荟萃分析（Meta-analysis）等正式证据综合研究（evidence synthesis research）**。不得因为当前正在写 Introduction、文献回顾段落或某个分析章节，就混用整篇文稿的写作流程。

随后调用 `research-standards` 核验当前 study design / publication target 对应的 reporting guideline；报告规范用于检查透明度和完整性，不替代 Design、Analysis 或 Interpretation。若目标属于系统综述、范围综述或荟萃分析，而正式检索、筛选、质量评价、数据提取或综合 provenance 尚未完成，退出 Communication 返回 `akira-research` 补齐科研流程，不能用普通综述写作替代方法学过程。

## 2. 从 canonical source 写作

只从当前 `RESEARCH.md`、`research.sqlite`、Design / Study / Data / Analysis artifacts、原始论文及已完成 Interpretation 取事实。写作中发现新的科学解释或关键事实缺口时返回 `interpretation` 或其他对应 Skill，先更新 canonical state，再继续传播。

完整 Claim traceability、Results / Discussion / Methods、figure / table、citation 与 communication provenance 规则见 [`references/CONTRACT.md`](references/CONTRACT.md)。

- 原始研究论文及同类 research thesis / report → [`references/RESEARCH-ARTICLE-WORKFLOW.md`](references/RESEARCH-ARTICLE-WORKFLOW.md)：完整盘点写作材料后，采用“主要结论 → Results → Discussion → 反推 Introduction → Methods → Abstract / Title → Supplement / Appendix”的默认写作顺序，并在完整 prose 前用小标题与 Figure / Table 搭出 Results 骨架；
- 普通叙述性文献综述 → [`references/REVIEW-WORKFLOW.md`](references/REVIEW-WORKFLOW.md)：先固定 Review Question / Scope，再完整盘点文献材料、建立主题分类、做跨论文综合、形成理论/概念框架并推出真实 gap；不得套用原始研究论文的 Results / Discussion 流程；
- 所有写作类型的段落衔接、反向提纲（reverse outlining）、英文逻辑连接词、结论强度和术语一致性 → [`references/WRITING-EXPRESSION.md`](references/WRITING-EXPRESSION.md)；
- 完成长篇 draft 后、进入 reviewer-style review 前，以及 revision 后最终交付前 → [`references/audit/INTEGRITY-AUDIT.md`](references/audit/INTEGRITY-AUDIT.md)，核验 Claim↔source、数字/统计、scope、citation 与 revision drift；
- reviewer response、major/minor revision、学位评审修改 → [`references/REVISION-WORKFLOW.md`](references/REVISION-WORKFLOW.md)，每条意见先固定验收标准，先核验实际 revised manuscript / artifact，再读取 response letter 判断其是否准确描述真实修改；
- publication figure / multi-panel figure / Figure revision → [`references/FIGURE-WORKFLOW.md`](references/FIGURE-WORKFLOW.md)，先固定 Figure-level scientific question、最窄 Claim 与 panel 的证据作用，再做版式和渲染，并在最终实际尺寸逐 panel QA；
- 正式 manuscript / review / revision 的 citation 核验 → [`references/audit/CITATION-AUDIT.md`](references/audit/CITATION-AUDIT.md)，分别检查文献身份、Claim–source 支持关系和目标 venue 格式；DOI 能解析、metadata 正确或 bibliography 编译成功都不能替代 source 是否真正支持当前 Claim 的核验。

## 3. Figure / table 边界

用于分析诊断或形成 scientific result 的图属于 `analysis`。Publication figure / panel composition / layout 属于本 Skill，但必须从已登记的 analysis result 或其他 canonical artifact 派生，不能通过人工排版改变结果含义。正式论文 Figure 按 [`references/FIGURE-WORKFLOW.md`](references/FIGURE-WORKFLOW.md) 组织：Figure 与 panel 按科学问题和证据作用规划，不按已有文件、metric 或模板机械拼接。

## 4. 保持证据层级

Title、Abstract、Discussion、Conclusion、图注和 schematic 都不得比当前 evidence boundary 更强。Association、causality、mechanism、translation 与 population / system scope 在所有传播位置保持一致。

完成标准：传播产物已经按正确写作类型完成对应 workflow，可追溯到稳定科研版本；若存在正式 Methods / Results，则分别与实际执行和 outputs 一致；重要 Claim / limitation / uncertainty 均有依据，且采用了当前适用 reporting guideline。
