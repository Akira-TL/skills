# Research Interpretation Contract

Interpretation 的任务是把项目 Analysis 结果与已有 literature evidence 放回当前 Active Uncertainty，判断哪些解释被区分、哪些只被限定、哪些仍 unresolved。它不是把结果改写成更强的故事；Observation / estimate 与项目 Claim 必须继续分层。

## 1. 输入

进入 `INTERPRETATION` 时至少需要：

- 当前 Active Uncertainty；
- [`HYPOTHESIS.md`](HYPOTHESIS.md) 中的 competing hypotheses / predictions；
- [`ANALYSIS.md`](ANALYSIS.md) 要求下产生的可重建结果、diagnostics 与 sensitivity；
- 与目标问题相关时，通过 [`RESEARCH-SYNTHESIS.md`](RESEARCH-SYNTHESIS.md) 得到的 literature evidence boundary。

如果 primary result 仍存在未解决的数据、model 或 design failure，使 target contrast 本身不可解释，先回上游解决，不把技术失败解释成科学结论。

## 2. Observation → Claim gate

先写“结果直接显示什么”，再判断能提出什么 Claim。项目结果的 claim 层级沿用：

- `descriptive`：目标数据/系统中发生了什么；
- `association`：变量之间在明确设计下共同变化；
- `causal`：设计与 identification 足以支持 intervention/exposure 对 outcome 的因果效应；
- `mechanistic`：不仅有效应，而且关键中介/路径经过直接扰动、mediation/rescue 或等价判别证据；
- `speculative`：可作为下一轮解释或研究方向，但尚未达到前述层级。

Analysis 的统计强度不能越过 Design 的 identification 边界。观察性数据即使 `P` 很小、样本很大，也不会因此自动成为 causal evidence。

## 3. 与 competing hypotheses 对照

对每个关键 result 明确：

```text
Observed result
Which hypothesis predicted it?
Which competing hypothesis also remains compatible?
Which hypothesis is weakened within what scope?
What assumption is required for this interpretation?
```

只有 discriminator 对 competing hypotheses 给出不同预测、measurement 真正观测到该差异、且主要 alternative explanation 被设计/分析处理后，才更新 hypothesis 状态。

`favored` 不是“证明”。即使 H1 比 H2 更符合结果，也必须保留仍兼容的 H3、scope 和 measurement boundary。

## 4. Literature + project evidence

文献与项目自身结果按 evidence unit 综合，不按论文数量或“与我们一致”投票。

需要区分：

- 项目结果是否独立 replication，还是使用相同 cohort / dataset / reference；
- 文献 observation 与本项目 estimand 是否在 population、exposure、measurement、time 和 unit 上对齐；
- 跨物种、跨 assay、跨 taxonomic level 或 proxy measurement 的 inference gap；
- contradiction 是否可由 boundary condition / heterogeneity 解释；
- Critical Issues 是否降低某条 literature evidence 的 directness 或 confidence。

文献用于改变项目解释时，应能通过 Paper ID / DOI 与原始 Observation / Issue 回溯；项目结果则回到 analysis artifact。

## 5. Null、negative 与 contradiction

`P > 0.05` 不自动证明无效应。Interpretation 根据 effect estimate、interval、precision 与 decision boundary 判断它属于：

- 数据仍太不精确，`unresolved`；
- 排除了事先定义的 meaningful effect 范围，在该 scope 下支持 negligible / absent effect；
- 与某个 hypothesis 的明确预测相反，构成 weakening / contradiction；
- measurement / design failure 导致没有可解释信息。

同样，显著但极小、边界不稳定或只在 post hoc subgroup 出现的结果不能仅靠显著性升级重要性。

## 6. Mechanism gate

“与机制一致”与“机制被建立”分开。

机制 Claim 通常至少要求：

- proposed mediator / pathway 被直接测量；
- time order 与因果方向合理；
- mediator/pathway 的 perturbation、mediation、rescue 或其他 discriminator 能排除仅仅相关/下游响应；
- 关键 alternative pathway 得到足够处理。

基因组功能潜力、单个 transcript、相关 metabolite、histology proxy 等可以提供 mechanistic lead / indirect support，但不自动构成 mediation proof。

## 7. External validity 与 translation

Interpretation 明确结论只覆盖实际 study population / experimental system / dose / time / context。跨到其他性别、年龄、物种、菌株、疾病、环境或治疗场景时重新标记 inference gap。

动物 intervention 可以直接支持该动物模型中的 causal effect，但人类疗效、安全性或 treatment claim 需要对应的人体 evidence；prevention / preconditioning 设计不能改写成治疗 established disease。

## 8. 更新 Research State

一次 Interpretation 结束后更新 `RESEARCH.md`：

- `Current State`：只写仍影响路线的最窄 evidence boundary；
- `Active Uncertainty`：若已解决则关闭并从 Open Threads / synthesis 中选择新的 primary；若只缩小则按 [`ACTIVE-UNCERTAINTY.md`](ACTIVE-UNCERTAINTY.md) 重写 gap / explanations / next evidence；
- `Active Work`：指向下一条真正能降低 uncertainty 的动作；
- `Open Threads`：保存重要但当前不追的问题；
- `Key Decisions`：记录仍影响路线的解释/设计决定。

不要把完整结果表、文献摘要或历史演化堆进 `RESEARCH.md`。

## 9. 完成条件

Interpretation 完成时必须能清楚回答：

1. 数据直接显示了什么？
2. 哪个 Claim 层级得到支持，scope 是什么？
3. 哪些 competing hypotheses 被 favor / weaken / ruled out within scope？
4. 哪些 alternative explanations 仍然成立？
5. literature 与本项目 evidence 在哪里一致、冲突或只能间接连接？
6. 当前最窄、最可辩护的结论是什么？
7. primary Active Uncertainty 是否改变，下一条最有信息增益的 evidence 是什么？

如果第 7 项仍能由文献、分析或设计动作推进，就继续科研循环；Communication 只在确有传播/写作目标时进入，不是 Interpretation 后的强制下一阶段。
