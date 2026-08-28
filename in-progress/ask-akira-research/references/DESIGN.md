# Research Design Contract

Design 的任务是把 Hypothesis set 中的 discriminator 变成能够实际获得判别性 evidence 的研究方案。先定义要区分什么、测什么、比较什么，再选择实验技术；“做一个更大的实验”本身不是设计目标。

## 1. 进入条件

只有当 [`HYPOTHESIS.md`](HYPOTHESIS.md) 已经明确：

- target Active Uncertainty；
- 主要 competing hypotheses；
- 至少一个可观测 discriminator；
- 现有数据/分析不足以取得该 evidence；

并且需要新的 sampling、measurement、control、follow-up 或 intervention 时，才进入 `DESIGN`。

如果已有数据可以直接检验 discriminator，进入 `ANALYSIS`；如果缺的是现成文献事实，回到 literature/evidence retrieval。

## 2. 从 estimand / target contrast 开始

设计首先写清希望由数据识别的 target，而不是先列技术流程。至少明确：

- **Population / system**：结论针对谁或什么系统；
- **Exposure / intervention / condition**：比较的因素；
- **Comparator**：相对于什么；
- **Outcome / measurement**：实际观测变量，而不是抽象概念；
- **Time**：暴露、测量、随访或响应窗口；
- **Unit of inference**：真正独立的 biological / participant / experimental unit；
- **Target contrast / estimand**：什么差异、效应或关联会用于区分 hypotheses。

若无法把 discriminator 写成可测 target contrast，设计尚未开始完成。

## 3. 项目设计 artifact

当设计需要独立保存时，按需创建 `designs/<slug>.md`。它是该研究动作的 canonical design artifact；`RESEARCH.md` 只保留当前 Active Work 和 pointer。Design 一旦成为真实数据产生或未来结果判别的依据，使用 `research-db record-design` 登记其关联 Hypothesis Set、主要估计目标、主要结局、实验单位、feasibility 状态和 artifact path；冻结时记录真实 Git `freeze_commit`。数据库不复制完整组别表、预测矩阵或判定边界正文。

推荐结构：

```text
# Design: <name>

## Target Uncertainty

## Hypotheses and Discriminator
- H1 predicts ...
- H2 predicts ...
- Target evidence: ...

## Estimand / Target Contrast

## Population / Experimental System

## Sampling and Experimental Unit

## Groups / Exposure / Intervention / Comparator

## Measurements and Timepoints

## Controls and Bias Protection

## Primary Analysis Alignment

## Precision / Sample Size Rationale

## Decision Boundary

## Exploratory Analyses

## Feasibility / Ethics / Access Constraints

## Freeze and Amendments
```

不要求每个项目机械填满所有标题；只保留影响识别、可重复性和解释边界的部分。

## 4. Identification 与 bias protection

Design 必须主动检查什么会让 target contrast 不能回答原问题：

- confounding 与共同原因；
- reverse causality / temporal ordering；
- selection / attrition / missingness；
- pseudoreplication 与 non-independence；
- batch 与 processing order；
- contamination / carry-over；
- measurement specificity、sensitivity、calibration 与 detection limit；
- observer / allocation bias；
- compositional、normalization 或 proxy-measurement 限制；
- post-treatment adjustment / collider 等由分析引入的偏差。

根据实际设计选择 randomization、blocking、matching、blinding、negative/positive controls、technical controls、repeated measures 或其他保护措施；不把这些词作为模板装饰。

若干预是粪菌悬液、盲肠内容物、细胞制剂、血浆、组织提取物等**复杂生物材料**，必须区分“材料来源/整体制剂的干预效应”与其中某个目标成分的效应。完整移植物同时携带活微生物、代谢物、宿主来源成分或其他可生物活性物质时，阳性转移结果不能仅凭目标成分存在就归因于该目标成分。若科研问题要求把效应归因于活微生物或另一具体成分，需根据可行性加入能够区分共同转移成分的对照（例如标准化洗涤、滤液/灭活/载体对照或其他等价判别操作）；如果无法做到，则把 estimand 和 Claim 收窄到实际被随机化的整体干预。

同样，**某条件下的因果效应**与**对该条件的特异反应/易感性效应**必须分开。若所有实验单位在结局阶段都处于同一个挑战条件，设计可以识别该条件下 intervention 的效应；除非另有相应条件对照并估计 intervention × condition 的交互或等价 target contrast，否则不能把这个效应改写为“增加了对该挑战的特异易感性”。

## 5. Primary 与 exploratory 边界

用于改变 hypothesis 状态的关键 discriminator 必须在观察对应结果前明确为 primary / confirmatory target，包括主要 outcome、contrast、time window 和 decision boundary。

可以同时保留 exploratory measurements，但它们产生的是新线索或新 hypothesis，不应在结果出现后回写成“原本就预测到”的 confirmatory evidence。

设计进入数据产生或目标结果可见之前，记录一个 **freeze point**（例如 Git commit），并确保关联的 Hypothesis Set 已在同一或更早提交中冻结。之后影响 estimand、primary outcome、关键 exclusion、group definition 或 primary analysis 的变化作为 amendment 明示原因和发生时点；Git history 保存具体版本。存在尚未解决的设施、伦理、样本来源或精度参数时，Design 可以冻结为“科研设计已完成但不可立即执行”，不得把 unresolved feasibility 改写成 execution-ready。

## 6. Sample size / precision

样本量依据 discriminator 所需的可识别精度设计，而不是只追求 `P < 0.05`。根据问题使用 effect-size uncertainty、confidence interval width、power、expected event rate、variance、dropout、cluster/repeated-measure structure 或 simulation 等合理依据。

若没有可信 effect size，不伪造精确 power；可以用 pilot / feasibility 目标、precision target 或 sensitivity analysis 表达不确定性。

## 7. Analysis alignment

Design 在数据产生前至少说明 primary analysis 需要尊重的结构：

- unit of inference；
- pairing / repeated measures / clustering；
- planned covariates 与其因果角色；
- primary contrast；
- multiplicity family；
- missing-data / censoring 原则；
- effect estimate 与 uncertainty 表达。

这里不写完整分析代码，但要保证未来 Analysis 不会用与设计不匹配的统计单位或比较方式。

## 8. Decision boundary

在结果出现前写明什么模式会：

- favor H1 over H2；
- weaken H1；
- 仍然无法区分；
- 暴露 measurement / design failure，使结果不能用于 hypothesis 判断。

单个 `P > 0.05` 默认属于“可能无法区分”，除非设计的 precision 足以排除事先定义的有意义效应范围。

## 9. 完成条件

Design 可以按 [`DATA.md`](DATA.md) 进入 Data 阶段时，至少满足：

1. discriminator 已转换成明确 estimand / target contrast；
2. independent unit、groups/comparator、measurements 与 time 已定义；
3. 主要 confounder / bias 与相应 control 已处理或明确成为限制；
4. primary analysis 与 multiplicity / dependence 结构对齐；
5. precision / sample-size rationale 足够解释为什么该设计有机会区分 hypotheses；
6. decision boundary 与 freeze point 已明确，关联 Hypothesis Set / Design canonical artifact 已进入结构化 provenance；
7. ethics、样本、设备、数据访问等现实前置条件已识别，并明确 Design 是 execution-ready 还是仍有 feasibility blocker。

存在必须由用户、伦理审批、样本来源、凭据或外部机构决定/提供的前置条件时，在这里停止并明确请求对应的人类输入；不要用假设值继续伪造可执行设计。
