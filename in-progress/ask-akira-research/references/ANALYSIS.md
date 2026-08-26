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

Primary Analysis 先执行 Design 预先定义的 contrast。任何重要偏离都记录为 amendment，并说明它发生在看见什么结果之前/之后。

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

## 8. Result artifact 与科研 Observation

当前项目自身 Analysis 的结构化 Observation 尚未固化进 `research.sqlite`（现有 `observations` 仍绑定 Paper）。因此真实数据工作流验证完成前：

- 数值结果和图表的 canonical source 保持为可重建 analysis artifact；
- `RESEARCH.md` 只更新会改变当前路线的高层 result boundary；
- 不把项目结果伪装成 literature Observation 写进 paper-bound tables。

当多项目实践表明 project Observation / analysis run 的稳定字段后，再通过 migration 扩展数据库，而不是现在提前复制 literature schema。

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
