---
name: interpretation
description: 把 Analysis result、Study/Design 边界与 literature evidence 综合成受证据约束的科学解释；当需要区分 Observation 与 Claim、更新 Hypothesis 状态、判断 causal/mechanistic scope、处理 contradiction 或产生新 Research Question 时使用。
---

# Interpretation

`interpretation` 负责科学判断，不负责论文叙事包装。它把 Observation / estimate 放回 Research Question、Design、Hypothesis 与 literature evidence 中，形成最窄、可追溯的 Claim，并把新的 uncertainty / branch 返回 `research-tree`。

## 1. 确认输入可解释

至少读取当前 Research Question / Active Uncertainty、相关 Design / Study 边界、Analysis result 与 diagnostics；有 Hypothesis 时读取 prediction / discriminator；需要外部证据时读取 `literature` 形成的 evidence boundary。

若 target contrast 因数据、measurement、study execution、model 或 design failure 仍不可解释，先返回对应 Skill 修正，不把技术失败解释成科学结论。

## 2. Observation → Claim

先写“数据直接显示什么”，再决定允许提出什么 Claim。Claim 层级、状态与过程、独立重复验证、随机试验/缺失/不依从、mechanism、external validity 与 contradiction 的完整 gate 见 [`references/CONTRACT.md`](references/CONTRACT.md)。

科学表述不能超过 Design identification、measurement validity 和 Analysis robustness 能支持的范围。先判断当前证据识别的是静态状态、变量关联还是时间/过程变化；只有设计真实识别了过程时才使用带过程含义的科学术语。同一 Dataset 内不同材料、亚组或分析规格的一致方向只能按其真实依赖结构描述，不能自动称为独立重复验证。统计显著性不能单独升级因果、过程或机制层级。

## 3. 综合 evidence

跨论文和项目自身 evidence 按 evidence unit、independence、directness、scope 与 Critical Issue 综合，不按论文数量投票。需要形成项目级 evidence synthesis 时读取 [`references/EVIDENCE-SYNTHESIS.md`](references/EVIDENCE-SYNTHESIS.md)。

Observation 对 Hypothesis / Claim 的 `supports`、`weakens`、`contradicts`、`qualifies` 等关系必须有 canonical basis；没有可追溯证据时保持 unresolved。

## 4. 更新研究结构

Interpretation 完成后：

- 更新当前 Claim 与 scope；
- 有 Hypothesis 时更新其 evidence state；
- 重新写最窄 Active Uncertainty；
- 新结果产生独立问题时创建新的 Research Question / branch；
- 将新对象和关系交给 `research-tree`；
- 把控制权交回 `akira-research` 决定下一动作。

写作过程中若发现新解释，仍应回到本 Skill 完成科学判断后再进入 `communication`。

完成标准：能够区分数据直接显示什么、允许支持什么 Claim、哪些解释被削弱或仍兼容、哪些 inference gap 仍存在，以及当前最有判别力的下一条 evidence 是什么。
