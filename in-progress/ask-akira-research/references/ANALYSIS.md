# Research Analysis Contract

Analysis 的任务是用已经冻结、可追溯的数据去估计 [`DESIGN.md`](DESIGN.md) 定义的 target contrast，并判断结果是否真正区分 [`HYPOTHESIS.md`](HYPOTHESIS.md) 中的 competing hypotheses。统计显著性不是 Analysis 的终点；effect、uncertainty、assumption 与 sensitivity 一起决定结果能支持到什么层级。

## 1. 进入条件

进入 `ANALYSIS` 前至少确认：

- 当前 primary Active Uncertainty 与 target discriminator 仍明确；
- 使用的数据满足 [`DATA.md`](DATA.md) 的 provenance / freeze / sample identity 条件；
- unit of inference、primary contrast、outcome 和主要 dependence structure 已知；
- confirmatory target 与 exploratory work 已区分。

缺少关键 raw/curated data、样本映射或访问授权时退回 `DATA`，不能用模拟值替代真实分析。

## 2. Analysis artifact

需要独立分析时按需创建 `analysis/<slug>/`，至少保留一个简洁 `README.md` 作为该分析的人类入口，并把脚本、配置、输入 pointer 和结果放在其下或清晰指向其他位置。

`README.md` 至少回答：

```text
Question / target contrast
Data freeze / input pointers
Unit of inference
Primary analysis
Exploratory analyses
Key assumptions
Outputs
Reproduction command / entrypoint
Result boundary
```

核心数值结果必须能从冻结输入和代码重新生成；Notebook 可以用于探索，但不应成为唯一不可重放的 primary-result source。

## 3. Design alignment

Primary Analysis 先执行 Design 预先定义的 contrast。任何重要偏离都记录为 amendment，并说明它发生在看见什么结果之前/之后。若该 Analysis 实现的是已经登记到 `research.sqlite` 的 Research Design，使用 `record-analysis` 时必须通过 `design_slug` 建立显式结构化连接；不能只复制相同的 estimand/uncertainty 文本来假装两者已经对齐。确认性 Analysis 的 Design 必须先冻结，且 Design freeze 必须早于或等于 Analysis 的结果前 freeze。

至少检查：

- paired / repeated / clustered 数据是否按真实 dependence 建模；
- technical replicate 是否错误膨胀 biological `n`；
- covariate 是否与 estimand 的因果角色一致，避免不当 post-treatment adjustment / collider；
- group、time、exposure 与 outcome 编码是否与 Design 一致；
- multiplicity family 是否按预先定义或科学问题正确处理；
- censoring、detection limit 和 missingness 是否被统计模型正确表达。

## 4. Estimate first

结果优先报告与科研问题直接相关的：

- effect estimate / contrast；
- confidence / credible interval 或其他 uncertainty；
- sample size / independent units；
- model / test definition；
- multiplicity-adjusted result（若适用）；
- raw / adjusted result 的适用范围。

`P` value 可以存在，但不能替代 effect magnitude 与 precision。`P > 0.05` 只说明当前检验没有提供足够证据反对相应 null model；只有区间/precision 足以排除事先定义的 meaningful effect 时，才可用于支持“在该范围内效应很小/不存在”。

## 5. Diagnostics 与 sensitivity

Primary result 进入解释前应检查会改变结论的主要 model / data failure mode，例如：

- residual / distribution / variance assumptions；
- influential observations / outliers；
- convergence / identifiability；
- batch / site / run effects；
- alternative normalization / compositional treatment；
- missing-data assumptions；
- exclusion rule；
- covariate specification；
- random seed / split instability；
- model overfitting / data leakage；
- multiple plausible pipelines。

Sensitivity analysis 的目的不是寻找能变显著的版本，而是判断结论在哪些合理分析选择下稳定、在哪些边界下改变。

如果科研问题**明确询问某个函数形式是否足够**（例如线性时间趋势是否足以描述轨迹），必须直接检验该函数形式，而不是只展示一个更灵活模型后凭肉眼判断。比较线性、二次项、分类时间、样条等替代形式时，应尽可能保持数据窗口、独立推断单位和 dependence / random-effects structure 一致，使比较主要反映函数形式本身；若结构无法保持一致，必须说明比较同时改变了哪些假设，不能把差异全部归因于“非线性”。

## 6. Prediction test

每个用于更新 Hypothesis 状态的主要结果都必须回到 discriminator matrix：

```text
Observed result
H1 predicted
H2 predicted
Does the observation distinguish them?
What alternative explanation remains?
```

若 observed result 同时兼容多个 hypotheses，则标记为 `unresolved`，而不是选择叙事上最吸引人的解释。

## 7. Exploratory analysis

Exploration 可以用于发现：

- unexpected pattern；
- subgroup / boundary condition；
- candidate mechanism；
- data-quality issue；
- 新变量关系。

但探索后形成的新 prediction 进入下一轮 Hypothesis / Design，不回写成当前 confirmatory target。高维筛选、feature selection、模型调参和 subgroup discovery 必须避免训练/测试泄漏，并对发现与验证数据的独立性保持明确。

## 8. Analysis Run、Result artifact 与项目 Observation

真实纵向数据黑盒已经稳定暴露出一组值得进入 `research.sqlite` 的下游对象：Dataset、Analysis Run、Analysis Amendment 与项目自身 Observation。使用 `research-db record-analysis` 持久化它们，但仍保持以下边界：

- 数值结果和图表的文件本身仍是可重建 analysis artifact；SQLite 只保存语义、路径与 provenance；除主要 `code_path` 外，任何实际生成主要结果、敏感性结果或关键诊断的附加脚本/workflow 也必须作为当前 Analysis artifact（通常 `role=other`）登记，不能因为文件放在 `scripts/` 目录就游离于 completion provenance。结果前已经存在并参与确认性执行的脚本/配置标记 `timing_role=pre_result_support`，真正由分析产生的 estimate/diagnostic/figure/report 标记 `timing_role=result`；前者必须出现在 freeze 中，后者不得出现在 freeze 中；
- confirmatory Analysis 必须记录结果可见前的 Git `freeze_commit`，该提交应已经包含主要分析计划、代码和输入，但不能已经包含本轮结果 artifact；Analysis 进入 frozen/completed 后不得替换这个 freeze pointer。进入该 freeze scope 的文件在当前 Analysis 历史上必须保留冻结版本，`validate --completion` 同时检查“freeze 时存在”与“freeze 后的 Git 历史没有该路径的提交改写”；中间改写后再 revert 回原内容仍属于破坏冻结，不能只凭 HEAD 内容再次相同声称预先冻结；Analysis 首次完成时固定 `completed_at`，后续追加 provenance 不重记完成时间；
- 结果可见后新增的敏感性分析或规则进入 Analysis Amendment，并标明 `post_result`，不能静默改写冻结的 estimand / primary analysis；若需要修订已冻结代码、输入或计划，保留原冻结文件并以新增版本/artifact + amendment 表达，必要时建立新的 Analysis，而不是覆盖旧版本后继续沿用原 `freeze_commit`；
- 项目自身 Observation 写入 `project_observations`，必须指向当前 Analysis 的具体结果 artifact；不要把项目结果伪装成 literature Observation 写进 paper-bound `observations`；
- `RESEARCH.md` 仍只更新会改变路线的高层 result boundary，不复制完整结果表。

从 schema v14 起，Hypothesis Set 与 Research Design 已进入最小结构化 provenance，用于保存身份、canonical artifact 与结果可见前的 freeze commit。schema v15 进一步把确认性 Analysis 显式连接到其 Research Design，并在结果解释后保存不可覆盖的 Hypothesis Evaluation 事件；Analysis 在解释结果时必须回到这些已冻结对象，而不能只依赖结果出现后的叙述。单条 Prediction、Decision Boundary、单个 hypothesis 的逐项状态与项目 Claim 仍不为了“阶段对称”而强制建表；它们的完整科研语义继续保留在 canonical artifact 中。

## 9. 完成条件

Analysis 可以按 [`INTERPRETATION.md`](INTERPRETATION.md) 进入 Interpretation 时，至少满足：

1. primary contrast 已按 Design 或明确 amendment 执行；
2. effect、uncertainty、independent `n` 与 multiplicity 边界可解释；
3. 关键 diagnostics / sensitivity 已覆盖足以改变结论的 failure modes；
4. observed result 已与 competing hypotheses 的 predictions 对照；
5. confirmatory 与 exploratory 发现分开；
6. input → code → output 可以重建；
7. 能清楚说出结果区分了什么、没有区分什么。

若分析暴露了 sample mapping、measurement、design 或数据质量问题，使 target contrast 无法识别，就回到对应上游环节修正，而不是强行进入 Interpretation。
