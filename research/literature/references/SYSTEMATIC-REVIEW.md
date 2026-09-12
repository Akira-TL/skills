# 正式证据综合研究工作流

本文件用于系统综述（Systematic Review）、范围综述（Scoping Review）、荟萃分析（Meta-analysis）以及其他明确要求可复现检索、预定义 eligibility、正式筛选和证据综合的方法学研究。它不是普通 Literature Discovery 的“更认真版本”，而是一种需要结果前 protocol、可复现 search / screening provenance 和预先定义 synthesis plan 的研究设计。

Akira 不自创系统综述方法学标准。启动前必须调用 `research-standards` 核验当前领域、Review 类型、目标期刊 / funder 所适用的**当前权威方法学与 reporting guideline**；PRISMA、Cochrane、JBI、ROB 2、ROBINS-I、GRADE、SWiM 等只有在实际适用时才采用，不能把某一领域的工具变成所有系统综述的默认规则。

## 1. 先判定 Review 类型

不要把以下类型混成同一流程：

### 系统综述

核心是围绕明确 Review Question，以结果前 protocol 定义 eligibility、search、selection、extraction、quality / risk-of-bias appraisal 与 synthesis，再系统回答该问题。

### 范围综述

核心通常是映射领域概念、研究类型、证据覆盖、方法分布或知识缺口。它仍要求 protocol、可复现 search / selection 和透明 extraction，但不默认要求与 intervention systematic review 相同的 risk-of-bias、effect pooling 或 certainty grading。

### 荟萃分析

荟萃分析是对经过适当 selection / extraction 的 study-level quantitative data 进行统计综合。它通常依赖一个系统性 evidence-identification process，但“找到若干论文后把 effect size 放进模型”本身不是完整的 Meta-analysis research workflow。

当一个系统综述包含荟萃分析时：

```text
Design / protocol
→ Literature search + screening + source assessment
→ Data extraction Dataset
→ Analysis meta-analysis
→ Interpretation evidence synthesis
→ Communication report
```

Meta-analysis 的统计建模继续由 `analysis` 管理；Literature 不在阅读阶段自行计算 pooled effect。

## 2. Protocol 必须先于结果感知的正式筛选与综合

正式检索前，先由 `akira-research → design` 建立并冻结 Review protocol。Protocol 至少按当前适用方法覆盖：

```text
Review Question / Objective
review type
scope / population / concept / intervention / comparator / outcome / context（按类型选择）
eligibility criteria
information sources
search strategy development plan
search date / update policy
record management / deduplication
screening process
full-text eligibility process
exclusion-reason policy
data extraction fields
study-level quality / risk-of-bias method（若适用）
synthesis plan
meta-analysis effect measure / model family / heterogeneity plan（若适用）
subgroup / sensitivity plan（若适用）
reporting-bias / certainty framework（若适用）
protocol amendment policy
registration status / requirement
```

具体 Question 框架可以是 PICOS、PCC 或领域适用结构，但不因第三方模板默认强制所有 Review 使用 PICOS。

是否必须 preregister、使用哪个 registry、何时注册以及注册需要哪些字段，都由 `research-standards` 从当前权威来源核验。**存在 protocol artifact ≠ 已完成外部注册**；只有真实 registration record / identifier 才能写“registered”。

Protocol freeze 后发生方法变化时，保留原 frozen protocol，并记录 amendment 的时间、原因、受影响步骤以及是否发生在相关结果可见之前或之后；不得回写旧 protocol 让计划看起来从未改变。

## 3. Search strategy 必须可复现

SYSTEMATIC 模式下，每个正式 search run 至少保存：

```text
source / database / platform
完整 query / search expression
field / filter / date / language / study-type restrictions
search date
result count
export / retrieval route
protocol version
```

继续使用现有 `research-db record-search` / Search Run provenance；不要另建 review-only 搜索日志。

Search source 的数量不使用固定“至少两个数据库”作为 Akira 通用阈值。应按 Review Question、领域覆盖、灰色文献 / registry / citation chasing 需要以及当前方法学指南证明 information sources 足够；只使用单一来源时必须有可辩护的方法学理由，而不是因为检索方便。

正式检索与普通 Discovery 的关键区别：

- query 可以在 protocol 允许的开发 / validation 阶段迭代，但最终正式检索版本必须保存；
- 搜索日期和最后一次 update search 必须可追溯；
- citation chasing、registry、灰色文献或其他补充来源如果属于 protocol，就作为独立 Search Run 保存；
- 不能根据已看到的研究结论静默修改 query 以增加支持某一方向的 evidence。

## 4. Identity resolution 与 deduplication 在 screening 前闭合

同一 scholarly work 从多个数据库进入时继续用 DOI / PMID / stable identity 合并，并保留所有 discovery / search provenance。Deduplication 是 record management，不是 eligibility exclusion；不得用 `excluded` 伪造重复条目。

如果多个 report 属于同一 underlying study / cohort，需要在 synthesis 前建立 study-level relation，避免把同一参与者 / dataset 的多篇论文当独立 replication 或重复计入 pooled estimate。

## 5. Screening 必须使用预定义 eligibility，而不是“看起来相关”

常见过程是：

```text
records identified
→ title / abstract screening
→ reports sought / full-text acquisition
→ full-text eligibility
→ included studies / reports
```

具体阶段按当前方法学规范调整。

对每个 record / report：

- 使用 frozen eligibility criteria 判断；
- 不确定时保持 `pending / unresolved`，进入下一层证据获取，而不是凭摘要猜；
- full-text exclusion 必须保存具体 reason；
- acquisition failure 与 eligibility exclusion 分开：拿不到全文不等于“不符合纳入标准”；
- 在 eligibility criteria 中没有预定义、却在看见结果后新增的排除理由属于 amendment，必须记录。

是否需要两个独立 reviewer、如何 adjudicate disagreement、是否允许自动化筛选以及抽查比例，都由当前适用方法学决定。Agent 不能因为 guideline 建议 dual review 就虚构第二位独立 reviewer；若项目实际只有单一 reviewer / Agent-assisted screening，应如实记录 execution 和 limitation。

## 6. 全文获取与 Paper Reconstruction 仍使用 Akira Literature

纳入或可能纳入的论文继续按本 Skill 的 acquisition、Paper identity、artifact、Reconstruction 和 source locator 契约处理。SYSTEMATIC 模式不会因为有 screening spreadsheet 就降低全文证据要求。

但 system review 的 study-level extraction 不等于普通人类阅读 sidecar。对 Review protocol 指定的字段，应建立一致的 extraction schema / table，并把每个关键值指回具体 Paper / report / table / figure / supplement locator。

至少避免：

- 从 abstract 提取 main effect 而正文存在不同 analysis population；
- 把作者 Discussion 的解释当 outcome data；
- 多 report 同一 study 重复 extraction；
- 单位、timepoint、adjusted / unadjusted estimate 混用；
- 只抽取显著结果而遗漏 protocol 指定的 null / adverse / secondary outcome。

## 7. Data extraction 应形成 canonical Dataset，而不是只留在 Markdown

当跨 study extraction 要进入正式 quantitative / structured synthesis 时，把整理后的 study-level evidence table 提升为 canonical Dataset，由 `data` 管理 identity、字段定义、version、QC 与 freeze。

典型字段按 Review 类型和 protocol 决定，例如：

```text
study_id / report_id
population / sample
intervention / exposure / comparator
outcome definition
timepoint
effect measure
estimate
standard error / CI / variance information
n / events / denominator
adjustment set
study design
risk-of-bias / quality fields
source locator
```

不要要求所有 Review 使用同一 schema。字段必须在结果前 protocol 或 amendment 中有来源。

数据抽取的人工 / Agent / automation 角色、独立复核情况和 discrepancy resolution 应如实记录；不能用“validated”掩盖只有单次模型抽取的事实。

## 8. Study-level risk of bias / quality appraisal 选择适用工具

是否需要 risk-of-bias / critical appraisal，以及使用哪个工具，取决于 Review Question、study design 和当前权威方法学。

原则：

- 对每个 included study / outcome 按适用工具的 domain 实际评估，不仅贴一个 overall label；
- `not reported` 与 demonstrated bias 分开；
- 一个工具不适配当前 study design 时不能强行套用；
- appraisal 结果必须进入后续 synthesis / sensitivity / certainty 判断，而不是做完一张 traffic-light 图就结束；
- 作者、期刊声望、引用次数不能替代 risk-of-bias assessment。

Akira 不内置“RCT 永远高于所有 observational / qualitative evidence”的跨学科固定证据金字塔。Evidence quality 取决于**当前 Claim、study design、measurement、bias 与 discipline-appropriate method**。

## 9. 先判断是否适合 quantitative pooling，再做 Meta-analysis

不能因为有多个 effect estimate 就默认 pooling。进入 `analysis` 前先检查：

- target estimand / effect measure 是否可比较；
- populations、interventions / exposures、comparators、outcomes、timepoints 是否属于可辩护 synthesis set；
- study design 与 measurement 差异是否允许合并；
- dependence / shared cohort / multi-arm structure 如何处理；
- heterogeneity 是否代表可解释 variation，还是已经破坏同一 pooled target 的意义；
- protocol 是否预定义 subgroup / sensitivity / model family，或者当前修改属于 post hoc amendment。

若 pooling 合理，Meta-analysis 作为正式 Analysis：

```text
frozen extracted Dataset
→ record-analysis
→ Analysis Attempt
→ effect transformation / model / variance
→ heterogeneity / influence / sensitivity
→ result table / forest-plot table
→ Interpretation
```

统计结果优先报告 pooled estimate 与 uncertainty，并同时解释 study-level variation、model assumptions 和 sensitivity；不能只用 `I²` 的固定区间标签机械决定“异质性高/低”。

若 pooling 不合理，使用当前领域适用的 structured narrative / qualitative synthesis，而不是为了产生 forest plot 硬做 Meta-analysis。

## 10. Reporting bias、certainty 和 additional synthesis 只在适用时执行

Publication / reporting bias assessment、certainty-of-evidence framework、subgroup、meta-regression、network meta-analysis、diagnostic accuracy synthesis 等不是所有 Review 的固定步骤。

采用前必须：

1. 当前 Review Question 和 data structure 确实适用；
2. 方法在 protocol / amendment 中有记录；
3. `research-standards` 已核验当前方法学依据；
4. 样本 / study 数量和 measurement 足够使方法有可解释性。

GRADE 等 framework 不能被当作 Akira 自己的通用证据评分器。

## 11. Search update 与最终冻结

正式提交或最终解释前，根据 protocol / target guideline 检查是否需要 update search。最终至少固定：

```text
last_search_date
每个 information source 的最后 query
screening counts
full-text exclusions + reasons
included study / report set
extraction Dataset version
risk-of-bias / quality version
synthesis / Analysis commit
protocol + amendment history
```

如果 update search 新增 study，旧 synthesis 和 Communication source commit 失效，必须重新执行受影响 extraction、Analysis、Interpretation 和稿件更新。

## 12. SYSTEMATIC 与普通 Discovery 的 completion 不同

普通 Literature Discovery 以当前 Active Uncertainty 的概念饱和和 Candidate 队列闭合为核心；SYSTEMATIC 不使用“conceptual saturation”证明检索完整，也不要求为了满足 Discovery 门禁额外补造与 protocol 无关的 citation chasing。

SYSTEMATIC 的方法学完成至少要求：

1. frozen protocol / amendment history 存在；
2. protocol 规定的 information sources 已按可复现 query 实际检索；
3. deduplication 已闭合；
4. screening / full-text eligibility 已按预定义标准闭合，排除理由可追溯；
5. included sources 已完成 protocol 所需获取和 extraction；
6. 适用的 risk-of-bias / quality appraisal 已完成；
7. extraction Dataset 已 freeze（需要结构化 / quantitative synthesis 时）；
8. 适用的 Analysis / narrative synthesis 已完成并进入 Interpretation；
9. final / update search 状态明确；
10. current method/reporting standards 已核验。

现有 `research-db validate --completion` 继续用于检查共享科研对象、artifact、Git 和已实现 provenance 门禁，但**不能把 `discovery.ready_for_saturation=true` 解释成 Systematic Review 方法学已经完整，也不能反过来用 Discovery saturation 的缺失否定一个按 protocol 已闭合的 SYSTEMATIC search**。在数据库出现专门 SYSTEMATIC validator 以前，protocol artifact、Search Runs、screening/extraction records 与 downstream Dataset / Analysis provenance 是这条工作流的方法学事实源。

## 13. 交给 Communication 时提供什么

进入 `communication` 前至少提供稳定 source commit 和：

- Review Question / protocol / registration status；
- information sources、完整 search strategy 与日期；
- screening flow counts 和 full-text exclusion reasons；
- included study characteristics；
- extraction Dataset / evidence table；
- risk-of-bias / quality appraisal；
- quantitative Analysis 或 structured synthesis；
- sensitivity / heterogeneity / certainty（若适用）；
- protocol deviations / amendments；
- remaining limitations。

Communication 再按当前 reporting guideline 组织 Methods / Results / Discussion；不得在写稿阶段补造缺失的 systematic-review methods。
