# Research Communication Contract

Communication 的任务是把已经建立的研究状态、证据边界、方法与不确定性准确地转成论文、报告、摘要、图表、答辩或其他面向人的产物。传播形式可以变化，但科研 Claim 不能因为进入写作阶段而升级。所有术语选择、中文/英文首次出现方式、新概念命名和近义词使用统一遵守 [`ACADEMIC-LANGUAGE.md`](standards/ACADEMIC-LANGUAGE.md)。

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

Communication artifact 是派生输出，不形成新的科研事实源。正式进入传播前，应在 Analysis / Interpretation / Hypothesis Evaluation 与当前 `RESEARCH.md` 已稳定后形成一个明确的 **pre-communication canonical freeze commit**；传播产物必须声明自己基于哪个冻结版本。写作过程中发现一个重要事实只存在于草稿里时，先退出 Communication，回到应有 canonical source 持久化、重新形成稳定 source commit，再继续写。

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

若主要推断依赖尚未核验的独立实验单位、随机分配、抽样结构或其他识别条件，**标题和摘要同样必须保留这一条件性**。不能在正文中写“在名义独立记录假设下”，却在标题中无条件宣称“总体均值已经不同”或“处理有效”；应改用数据集层级描述，或明确写出必要条件/适用范围。

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

## 10. Communication provenance

从 schema v16 起，一次可独立交付的传播产物使用 `research-db record-communication` 登记最小 provenance：

- `source_commit`：传播开始前已经稳定的 canonical scientific evidence commit；
- `purpose` / `audience`：传播目标与受众；
- `communication_artifacts`：题目/摘要、方法、结果、讨论、图、图注、大众摘要、追溯表和生成脚本等实际文件；
- `timing_role=source_support|derived_output`：区分传播前已存在的支持文件与传播阶段生成的派生产物。

Communication Product 是工程审计对象，不是新的学术概念或科研事实源。数据库只证明“这些传播文件基于哪个科研版本、何时生成、是否被 Git 跟踪”；它不能自动证明稿件中的每一句 Claim 真正由 source 逻辑蕴含。

完成的传播产物必须满足：

1. `source_commit` 存在并是当前 HEAD 的祖先；
2. `derived_output` 在 source commit 中尚不存在，`source_support` 在 source commit 中已经存在；
3. source commit 之后若 Hypothesis / Design / Data / Analysis / Interpretation 等科学 canonical artifact 又发生变化，旧传播稿不得继续声称基于最新证据，必须重新审阅并选择新的 source commit；
4. 已登记传播文件进入 Git 完整性门禁，但这**不把它们提升为 canonical scientific source**；
5. 中文传播稿同样执行学术语言自审。已有成熟中文表述的术语，例如“处理（treatment）”“结局（outcome）”“溯源（provenance）”“确认性（confirmatory）”“探索性（exploratory）”，不得长期以裸英文替代中文学术表述。

`TRACEABILITY.md` 一类文件可以作为 derived audit view，但它只能指回 canonical evidence，不能自我引用成为科学依据；逐条 Claim 的逻辑支持关系仍由主模型科研审查。

## 11. 完成条件

Communication artifact 完成前检查：

1. 每个关键科研 Claim 可追溯；
2. Results 与实际 analysis outputs 一致；
3. Methods 与实际执行一致；
4. confirmatory / exploratory / post hoc 边界没有被抹平；
5. contradiction、negative result 和主要 limitation 没有因叙事需要被隐藏；
6. title / abstract / conclusion 没有比正文 evidence boundary 更强；
7. figure / table 可回到生成流程；
8. citations 身份与支持范围已核验；
9. 传播产物已经登记 `source_commit` 与实际 artifact provenance，且传播阶段没有在 source freeze 后静默改变科学 canonical evidence；
10. 中文稿件的标准术语与首次中英文表达已自审，标题/摘要没有因压缩语言而丢失关键条件性。

发现写作需要新的科学判断时，回到 Interpretation / Evidence Synthesis，而不是在 Communication 层临时创造结论。
