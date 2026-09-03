---
name: hypothesis
description: 把当前 Research Question 中真正竞争的解释转成有范围、有可观测预测和判别条件的 Hypothesis Set；当需要区分 competing explanations、形成结果前 prediction 或决定什么证据最有判别力时使用。
---

# Hypothesis

`hypothesis` 只处理确实需要假设推理的研究分支。探索性、描述性或单纯事实核验研究不强制经过本 Skill。

## 1. 确认进入条件

从 `research-tree` 取得当前 Research Question / Active Uncertainty。只有至少两个仍合理的 competing explanations，且下一步需要利用不同 prediction 区分它们时，才建立 Hypothesis Set。

若缺的是已有文献事实，路由 `literature`；若现有 Dataset 已足够判别，路由 `analysis`；若需要新的 sampling、measurement、control 或 intervention，完成预测后路由 `design`。

## 2. 形成可判别假设

每个 Hypothesis 明确 statement、scope、关键 assumptions、observable predictions 与能够实质削弱它的结果。预测必须在用于判别的新结果可见前形成，且落到真实可测 observation 层。

完整科研契约见 [`references/CONTRACT.md`](references/CONTRACT.md)。

## 3. 保存来源与冻结边界

区分用户提出、Agent 提议以及用户对 Agent proposal 的接受决定；接受探索不等于科学支持，也不改变原始来源。需要作为后续确认性 Design / Analysis 判别依据的 Hypothesis Set，按项目现有 `research-db` 契约登记并在结果前冻结。

## 4. 返回总 Router

完成后返回：Hypothesis Set、discriminator / decision boundary、需要的下一类 evidence、产生或更新的 research-tree 关系，以及仍未区分的解释。最终下一步由 `akira-research` 决定。

完成标准：主要竞争解释至少有一项可观测差异，且能明确说明现有数据、进一步分析或新研究设计中的哪一种最可能区分它们。
