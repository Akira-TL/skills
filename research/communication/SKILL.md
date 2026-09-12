---
name: communication
description: 把已经建立的 scientific state、方法、证据边界与 provenance 转成论文、报告、摘要、图表、补充材料、答辩或 reviewer response；当存在真实传播目标时使用。
---

# Communication

`communication` 负责科学表达，不负责创造新的科学结论。进入本 Skill 前，关键 Observation、Claim、Design / Study / Analysis 边界应已在 canonical research state 中稳定。

## 1. 确认传播目标与适用规范

明确产物类型、受众与用途。调用 `research-standards` 核验当前 study design / publication target 对应的 reporting guideline；报告规范用于检查透明度和完整性，不替代 Design、Analysis 或 Interpretation。

## 2. 从 canonical source 写作

只从当前 `RESEARCH.md`、`research.sqlite`、Design / Study / Data / Analysis artifacts、原始论文及已完成 Interpretation 取事实。写作中发现新的科学解释或关键事实缺口时返回 `interpretation` 或其他对应 Skill，先更新 canonical state，再继续传播。

完整 Claim traceability、Results / Discussion / Methods、figure / table、citation 与 communication provenance 规则见 [`references/CONTRACT.md`](references/CONTRACT.md)。对于 manuscript、thesis、长篇 research report，正式起草正文前还必须按 [`references/MANUSCRIPT-WORKFLOW.md`](references/MANUSCRIPT-WORKFLOW.md) 先完整盘点写作材料，再采用“主要结论 → Results → Discussion → 反推 Introduction → Methods → Abstract / Title → Supplement / Appendix”的默认写作顺序，并在完整 prose 前用小标题与 Figure / Table 搭出 Results 骨架。段落衔接、英文逻辑连接词、结论强度和术语一致性按 [`references/WRITING-EXPRESSION.md`](references/WRITING-EXPRESSION.md) 自审。

## 3. Figure / table 边界

用于分析诊断或形成 scientific result 的图属于 `analysis`。Publication figure / panel composition / layout 属于本 Skill，但必须从已登记的 analysis result 或其他 canonical artifact 派生，不能通过人工排版改变结果含义。

## 4. 保持证据层级

Title、Abstract、Discussion、Conclusion、图注和 schematic 都不得比当前 evidence boundary 更强。Association、causality、mechanism、translation 与 population / system scope 在所有传播位置保持一致。

完成标准：传播产物可追溯到稳定科研版本，Methods 与实际执行一致，Results 与实际 outputs 一致，重要 Claim / limitation / uncertainty 均有依据，且采用了当前适用 reporting guideline。
