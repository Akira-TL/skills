# Research Communication Contract

Communication 的任务是把已经建立的研究状态、证据边界、方法与不确定性准确地转成论文、报告、摘要、图表、答辩或其他面向人的产物。传播形式可以变化，但科研 Claim 不能因为进入写作阶段而升级。

## 1. 进入条件

`COMMUNICATION` 只在存在真实传播目标时进入，例如：

- manuscript / thesis / report；
- abstract / conference submission；
- figure / table / poster / presentation；
- methods / protocol documentation；
- collaborator / reviewer response；
- 项目阶段总结。

Interpretation 结束后没有传播需求时继续科研循环，不机械进入 Communication。

## 2. Canonical source 优先

写作前先从 canonical sources 取事实：

- 当前路线、Active Uncertainty 与项目级结论：`RESEARCH.md`；
- 文献详细证据：`research.sqlite` + 原始 paper artifacts；
- 项目结果：可重建 analysis artifacts；
- design / hypothesis / data provenance：对应项目 artifacts；
- derived evidence report / sidecar 只用于导航，不替代原始来源。

Communication artifact 是派生输出，不形成新的科研事实源。写作过程中发现一个重要事实只存在于草稿里时，先回到应有 canonical source 持久化，再继续写。

## 3. Claim traceability

所有实质科研 Claim 都必须能回答“依据是什么”：

- 文献 Claim → Paper ID / DOI + 对应 Observation / source locator；
- 项目 Claim → analysis artifact + target contrast / result；
- causal / mechanistic Claim → 对应 identification / discriminator；
- limitation / unresolved → 对应 Issue、design boundary 或 sensitivity。

引用作者 Discussion 中的推测不能代替数据证据。综述句若综合多篇论文，要确保每篇 citation 实际支持该句对应部分，而不是只“主题相关”。

## 4. 结果写作边界

Results 优先报告：

- population / sample / independent `n`；
- effect / estimate；
- uncertainty；
- relevant adjusted statistics；
- predefined primary versus exploratory status；
- key negative / null result；
- measurement / scope boundary。

不要用“显著改善”“明显促进”掩盖 effect magnitude 或 proxy nature。非显著结果不写成“没有差异”，除非 precision 足以支撑对应 absence boundary。

## 5. Discussion / Conclusions gate

Discussion 可以提出解释，但必须区分：

- directly supported conclusion；
- indirectly supported explanation；
- plausible mechanism；
- alternative explanation；
- unresolved question；
- future hypothesis。

Conclusions 使用 [`INTERPRETATION.md`](INTERPRETATION.md) 得出的最窄 evidence boundary，不在最后一段为了“impact”重新升级。Association、causality、mechanism、translation 的层级在标题、摘要、图示模型和结论中保持一致。

## 6. Methods 与 reproducibility

Methods 必须与实际 Design、Data 和 Analysis 对齐，而不是事后理想化：

- 实际 sample / exclusion / missingness；
- 实际 software / parameter / reference version；
- 实际 statistical unit / model / multiplicity handling；
- protocol amendment；
- exploratory / post hoc change；
- data / code availability 和访问限制。

若实际执行与 frozen design 不同，写清 amendment；不要把 post hoc 分析描述成预先计划。

## 7. Figures / tables

每个重要 figure / table 应能回到生成它的 analysis artifact 和 input freeze。图形选择不能改变科研结论：

- 显示真实 independent units / distribution when material；
- 轴、scale、normalization、error bar 含义明确；
- 不用截断轴、挑选 timepoint、隐藏 outlier 或选择性 panel 制造更强效果；
- figure annotation 的 significance 与正文 multiplicity 规则一致；
- derived / proxy metric 明确标注，不冒充直接 measurement。

## 8. Literature citation discipline

优先引用实际提供该事实/证据的原始论文。需要引用 review 时，明确它承担综述背景而不是原始 evidence。

引用前至少核对 title / DOI / identity 与实际内容；数据库 sidecar、Agent synthesis 或搜索 snippet 不是可发表 citation source。

## 9. Audience adaptation

面向不同 audience 可以改变术语密度、篇幅和结构，但不能改变：

- evidence directness；
- effect / uncertainty；
- causal level；
- population / system scope；
- known limitation；
- unresolved status。

面向大众时可以简化方法语言，但不能把“在特定小鼠模型中”压缩成“对人有效”。

## 10. 完成条件

Communication artifact 完成前检查：

1. 每个关键科研 Claim 可追溯；
2. Results 与实际 analysis outputs 一致；
3. Methods 与实际执行一致；
4. confirmatory / exploratory / post hoc 边界没有被抹平；
5. contradiction、negative result 和主要 limitation 没有因叙事需要被隐藏；
6. title / abstract / conclusion 没有比正文 evidence boundary 更强；
7. figure / table 可回到生成流程；
8. citations 身份与支持范围已核验。

发现写作需要新的科学判断时，回到 Interpretation / Evidence Synthesis，而不是在 Communication 层临时创造结论。
