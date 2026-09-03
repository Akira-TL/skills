# Research Design Contract

Design 的任务是把 Hypothesis set 中的 discriminator 变成能够实际获得判别性 evidence 的研究方案。先定义要区分什么、测什么、比较什么，再选择实验技术；“做一个更大的实验”本身不是设计目标。

## 1. 进入条件

只有当 [`hypothesis`](../../hypothesis/SKILL.md) 已经明确：

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

随机试验预计可能出现不依从（nonadherence）时，必须在结果可见前区分**随机分配效应**与**实际接受处理效应**。若科研问题针对分配某一处理策略的总体效果，主要目标通常是意向治疗效应（intention-to-treat effect, ITT effect），分组依据保持为随机分配，不因后续实际接受状态改变。若科研问题针对实际接受处理本身的因果效应，则必须另行定义目标总体与目标估计量，例如全部目标单位中的处理接受效应，或在明确识别条件下的依从者平均因果效应（complier average causal effect, CACE）/局部平均处理效应（local average treatment effect, LATE）。随机化本身不自动识别这些处理接受效应，因为实际接受处理与依从性属于随机分配后的变量；若采用工具变量（instrumental variable, IV）或其他识别策略，相关性、排除限制、单调性及其他所需假设必须根据具体设计明确，而不能由“研究是随机试验”这一事实代替。

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

当判别逻辑依赖不能被直接观测的**潜在构念（latent construct）**，并以某个代理测量（proxy measurement）或操作性阈值判断“该状态已经达到”时，必须单独检查**构念效度（construct validity）**。这项检查必须沿 measurement chain 递归到实际观测量：不能因为论文、数据库字段或既有研究把某个派生指标命名为“功能”“能力”“速率”“状态”或其他目标构念名称，就跳过它本身是否仍由浓度、丰度、模型输出或其他代理量推断得到的审查。领域中被称为“直接法”“参考方法”或“金标准”的方法也必须继续拆到实际观测量与计算步骤；若其主要输出仍由受控实验条件下的浓度、输入量、示踪数据、模型或归一化计算得到，应表述为相对于其他代理**更直接的生理/过程估计**，而不是与仪器原始观测量处在同一层级。只有方法真正直接观测目标过程、活性、通量或反应时，才按相应直接测量层级解释；否则继续按该实际观测量能够支持的层级收窄 estimand 与 Claim。随机化后续处理只能识别被随机化策略的效应，不能自动证明代理阈值等同于潜在构念真实成立。代理尚未在当前人群、时间尺度和操作条件下得到足够验证时，只能二选一：增加能够检验该构念的独立测量、重复测量或其他收敛证据；或者把 estimand、Hypothesis 与最终 Claim 收窄为“在该预定义代理状态下”的效应。代理达到阈值后仍观察到结局异常时，只要“代理没有真实反映潜在状态”仍是可行解释，就不能单凭该结果把异常归因于另一机制；这一分支必须进入 decision boundary 的 `unresolved` / `not_interpretable` 条件或明确的限定性解释。

若干预是粪菌悬液、盲肠内容物、细胞制剂、血浆、组织提取物等**复杂生物材料**，必须区分“材料来源/整体制剂的干预效应”与其中某个目标成分的效应。完整移植物同时携带活微生物、代谢物、宿主来源成分或其他可生物活性物质时，阳性转移结果不能仅凭目标成分存在就归因于该目标成分。若科研问题要求把效应归因于活微生物或另一具体成分，需根据可行性加入能够区分共同转移成分的对照（例如标准化洗涤、滤液/灭活/载体对照或其他等价判别操作）；如果无法做到，则把 estimand 和 Claim 收窄到实际被随机化的整体干预。

同样，**某条件下的因果效应**与**对该条件的特异反应/易感性效应**必须分开。若所有实验单位在结局阶段都处于同一个挑战条件，设计可以识别该条件下 intervention 的效应；除非另有相应条件对照并估计 intervention × condition 的交互或等价 target contrast，否则不能把这个效应改写为“增加了对该挑战的特异易感性”。

当问题涉及中介作用（mediation）或机制路径时，必须在结果前区分总效应（total effect）与具体的直接/间接效应估计目标。随机化处理并不等于随机化候选中介变量；若计划估计受控直接效应（controlled direct effect, CDE）、自然直接效应（natural direct effect, NDE）、自然间接效应（natural indirect effect, NIE）或其他中介效应，需明确候选中介的时间顺序、处理－中介交互、基线中介－结局混杂因素，以及是否存在**暴露诱导的中介－结局混杂因素（exposure-induced mediator–outcome confounder）**。存在这类处理后共同原因时，普通回归调整或标准自然效应分解不能仅凭处理随机化获得识别；应改用与目标 estimand 和因果结构相容的方法，或通过直接中介扰动、救援/阻断等设计取得更直接的机制判别证据。

## 5. Primary 与 exploratory 边界

用于改变 hypothesis 状态的关键 discriminator 必须在观察对应结果前明确为 primary / confirmatory target，包括主要 outcome、contrast、time window 和 decision boundary。

可以同时保留 exploratory measurements，但它们产生的是新线索或新 hypothesis，不应在结果出现后回写成“原本就预测到”的 confirmatory evidence。

设计进入数据产生或目标结果可见之前，记录一个 **freeze point**（例如 Git commit），并确保关联的 Hypothesis Set 已在同一或更早提交中冻结。之后影响 estimand、primary outcome、关键 exclusion、group definition 或 primary analysis 的变化作为 amendment 明示原因和发生时点；Git history 保存具体版本。存在尚未解决的设施、伦理、样本来源或精度参数时，Design 可以冻结为“科研设计已完成但不可立即执行”，不得把 unresolved feasibility 改写成 execution-ready。

## 6. 样本量与估计精度

样本量应根据区分竞争解释所需的**估计精度**进行规划，而不是只追求 `P < 0.05`。根据具体问题，可以依据效应量不确定性、置信区间宽度、统计功效、预期事件率、方差、脱落率、聚类/重复测量结构或模拟等进行样本量规划。

若没有可信的效应量依据，不伪造看似精确的功效分析；可以采用预试验/可行性目标、基于精度的样本量规划（precision-based sample size planning）或敏感性分析表达不确定性。

用于声称“恢复到基线附近”“达到等效”或区分两个 Hypothesis 的**等效性界值（equivalence margin）/判别界值**，必须同时说明其科学意义与 measurement repeatability / precision 是否允许这个界值被可靠区分。仅因为该界值“小于既往观察到的效应”不能构成充分依据。若目标中心重复测量误差、可靠性或领域上可接受的残余效应范围尚未知，可以把界值明确保留为结果前待锁定参数，并把 Design 标记为 non-execution-ready；此时不得把临时数值表述成已经得到科学论证的最终判别边界。后续锁定必须发生在主要结果可见前，并作为可审计的 pre-result amendment 保存。

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

Design 可以按 [`data`](../../data/SKILL.md) 进入 Data 阶段时，至少满足：

1. discriminator 已转换成明确 estimand / target contrast；
2. independent unit、groups/comparator、measurements 与 time 已定义；
3. 主要 confounder / bias 与相应 control 已处理或明确成为限制；
4. primary analysis 与 multiplicity / dependence 结构对齐；
5. precision / sample-size rationale 足够解释为什么该设计有机会区分 hypotheses；
6. decision boundary 与 freeze point 已明确，关联 Hypothesis Set / Design canonical artifact 已进入结构化 provenance；
7. ethics、样本、设备、数据访问等现实前置条件已识别，并明确 Design 是 execution-ready 还是仍有 feasibility blocker。

存在必须由用户、伦理审批、样本来源、凭据或外部机构决定/提供的前置条件时，在这里停止并明确请求对应的人类输入；不要用假设值继续伪造可执行设计。
