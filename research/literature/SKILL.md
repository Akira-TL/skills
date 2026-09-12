---
name: literature
description: 围绕科研项目的 Active Uncertainty 执行文献发现、全文获取路由、论文重建、批判性评估与跨论文证据综合；当需要用现有文献区分 competing explanations、核验方法或边界条件、寻找下一条判别性 evidence，或用户直接要求完整 Literature Research 时使用。继续使用同一 RESEARCH.md 与 research.sqlite，不替代 akira-research 的项目级科学状态与路线决策。
---

# Literature

本 Skill 负责文献发现、全文阅读、批判审阅与跨论文证据综合。已知目标论文的合法全文获取由 `literature-access` 负责；本 Skill 决定为什么找、哪些论文进入队列、读什么、如何批判以及文献 evidence 如何进入同一个科研项目。

## 0. 进入项目与科研边界

先定位当前科研项目并读取 `RESEARCH.md`，以其中的 Objective、唯一 primary Active Uncertainty、Current State 与 Open Threads 约束本轮文献工作。用户直接从零发起 Literature Research、当前尚无科研项目时，按 [`akira-research` 的项目状态契约](../akira-research/PROJECT-STATE.md) 建立最小项目；不维护第二套 literature-only research state。

项目级 `research.sqlite`、migration、CLI 与完成门禁继续使用 [`akira-research` 的数据库契约](../akira-research/RESEARCH-DB.md)。这些是共享科研项目的内部实现，不形成独立 Skill。所有人类可读科研表述遵守 [`ACADEMIC-LANGUAGE.md`](../akira-research/references/standards/ACADEMIC-LANGUAGE.md)。当前 Active Uncertainty 需要重写或拆分时读取 [`research-tree` 的 Active Uncertainty 契约](../research-tree/references/ACTIVE-UNCERTAINTY.md)；文献工作产生值得持续追踪的新科学猜想、用户判断或用户对猜想的明确决策时，按 [`RESEARCH-COLLABORATION.md`](../akira-research/references/collaboration/RESEARCH-COLLABORATION.md) 保留来源，不把 Agent-generated hypothesis 改写成用户观点。

论文 Reconstruction、Critical Audit、evidence-to-claim 判断和跨论文科研综合仍由当前主会话模型直接完成；获取、解析、检索、事务写入与校验工具只承担确定性工作，不代替科学语义判断。

### 完整工作流的执行闭环

用户要求完整 Literature Research，或 `akira-research` 已把当前动作正式路由到本 Skill 时，本轮进入闭环执行。除非出现必须由用户完成的全文登录/文件提供、权限或伦理等真实外部 blocker，或当前环境客观无法继续执行，否则持续推进到本轮 Literature completion gate 已实际运行并通过；工作量大、已经形成初步科学判断、已有可汇报的阶段结果、Candidate 队列尚未闭合、`discovery-status.ready_for_saturation=false` 或 `validate --completion` 尚未通过，都表示**继续执行下一项未闭合工作**，不是结束本次任务的理由。

闭环中的状态只按两类对外返回：

- `COMPLETED`：全文 acquisition / reading / Critical Audit / synthesis / canonical 写回 / Git 收口均满足本轮**当前模式适用的门禁**，并实际运行 `research-db validate --completion` 检查共享科研对象、artifact 与 Git provenance。`DISCOVERY` 还要求输出中的 `discovery.ready_for_saturation=true`、`literature.ready=true` 及适用的 `academic_language` / `project_state` 已闭合；`SYSTEMATIC` 则按 [`references/SYSTEMATIC-REVIEW.md`](references/SYSTEMATIC-REVIEW.md) 的 protocol-bound search / screening / extraction / appraisal / synthesis 条件闭合，不能拿 Discovery 的 conceptual saturation 代替系统检索完整性，也不能把与 frozen protocol 无关的 Discovery 饱和要求当成 SYSTEMATIC 完成条件。若全局 `completion=false` 仅由与本轮 Literature 无关的既存 Design / Analysis / Communication 等工作流 blocker 导致，不把它误判为 Literature 未完成，但必须如实保留该项目级欠账；
- `BLOCKED`：存在当前 Agent 无法自行解除且必须等待用户或外部条件的真实 blocker。此时保存已完成 provenance，在 `RESEARCH.md` 的 `Active Work` 写明 blocker 与解除条件，再向用户请求最小必要协同。

普通的 `pending`、`queued`、`not ready`、未完成深读、未完成 relation 或 working tree 尚未收口都不是第三种返回状态。不得以“本轮尚未完成”为最终答复替代继续执行。

## 1. Discovery，不把日常科研伪装成 Systematic Review

默认模式为 `DISCOVERY`：目标是高召回地理解领域、发现术语、方法、矛盾、边界条件与关键工作。检索式允许迭代；每次检索作为独立 Search Run 写入数据库，保留 purpose、source、query、filters、parent run、reason、result count、what we learned 与 next decision，并显式记录 `discovery_method`：`seed_search | query_expansion | backward_citation | forward_citation | related_work | method_search | update_search | exact_work | other`。`exact_work` 只表示已知论文的定向检索，不计作独立的 discovery strategy。

只有用户明确需要系统综述（Systematic Review）、荟萃分析（Meta-analysis）、范围综述（Scoping Review）或可发表的正式系统检索时才进入 `SYSTEMATIC`；完整方法学按 [`references/SYSTEMATIC-REVIEW.md`](references/SYSTEMATIC-REVIEW.md) 执行，不用 Discovery 的 iterative search / conceptual saturation 规则冒充系统综述。SYSTEMATIC 先由 `design` 冻结 Review protocol，再由本 Skill 执行 protocol-bound search、deduplication、screening、全文获取和 study-level extraction；需要正式结构化 / 定量综合时把 extraction 提升为 canonical Dataset，Meta-analysis 交给 `analysis`，最终 evidence boundary 交给 `interpretation`。

Discovery 采用循环：

```text
Active Uncertainty
→ seed search
→ terminology / author / method learning
→ query expansion
→ backward / forward citation chasing
→ related-work search
→ disconfirming / boundary search（当前已有主要判断时）
→ new search run
→ conceptual saturation
```

**不能只搜索支持当前工作假设的证据。** 一旦当前 Active Uncertainty 已经形成主要 Claim、competing explanation、preferred method / mechanism 或明显倾向的研究路线，在宣布 conceptual saturation 前主动设计至少一轮以“什么证据会推翻、削弱或限定当前判断”为目的的检索。可以针对：相反结果、失败复现、negative / null evidence、不同 population / condition、关键 alternative explanation、method failure / known bias、boundary case 或当前路线的直接 critique。该检索仍按实际策略登记为 `query_expansion`、`related_work`、`method_search`、citation chasing 或 `other` 等真实 `discovery_method`，不要为了新规则伪造不存在的枚举。

若反证/边界检索没有新增 Candidate，也保存真实 `result_count=0`、query / filters、`what_we_learned` 与检索边界。**“没有找到反证”只说明当前检索未找到，不等于反证不存在，更不能自动把 Claim 升级为 confirmed。** 若当前任务只是用户指定单篇 exact work、纯术语/方法查找，或尚未形成任何可被反驳的当前判断，不机械补造反证检索。

检索源按学科、问题类型与需要的证据类型选择，不把 Google Scholar 或任何单一入口当作默认全集。生物医学问题优先使用 PubMed / NCBI、Europe PMC 等领域数据库；需要引文网络时使用 Web of Science（WoS）、Scopus 等；综合发现可结合 Google Scholar、OpenAlex、Crossref；预印本、临床注册、数据/代码仓库等按问题需要进入独立 Search Run。不同来源发现同一 scholarly work 时继续按 DOI / PMID 等稳定身份合并，不把来源数量当作独立证据数量。

搜索停止依据是相对当前 Active Uncertainty 的边际知识增益：连续检索与引用追踪不再产生新的重要方法、观察、解释、矛盾、边界条件、研究设计或基础工作时，可以认为 discovery 达到当前目的的 saturation；不以固定论文数量作为停止条件。

在正式声称实践性概念饱和（practical conceptual saturation）前必须运行 `research-db discovery-status`。`core + relevant` 和 `high + relevant` Candidate 都必须已经 `acquired` 或经过完整获取流程后明确 `unavailable`；高优先级论文不能再用 `defer_reason` 绕过全文获取与审阅。`relevance_status=pending` 不能遗留；稳定 DOI/PMID 重复必须先合并。对于包含至少 2 个相关 Candidate、且实际执行了主题检索或相关工作扩展（related-work）的文献发现（Discovery），Candidate 队列闭合本身不等于饱和：必须至少记录一次真实的后向或前向引用追踪（backward/forward citation chasing），并且检索轨迹至少覆盖两个发现策略家族（discovery family）。仅对用户给定的已知论文做定向获取（exact work）不属于饱和声明，不强制补造主题检索。引用追踪即使没有新增 Candidate，也要作为 `result_count=0` 的真实检索运行（Search Run）保存本轮获得的信息与下一步决定。工具返回 `ready_for_saturation=false` 时不得仅凭主观判断宣布饱和。

每次真实搜索结束后用 `research-db record-search` 原子持久化 Search Run 与本次保留的 Candidate；同一论文在 seed search、query expansion 与 citation chasing 中重复出现时应复用 Candidate，并保留每个 `search_run_candidates` 发现边。identity resolution 只改变同一 scholarly work 的身份信息，不应通过 `excluded` 制造“重复论文”记录；发现旧 Candidate 与新稳定 DOI/PMID 实际属于同一 scholarly work 时，用 `research-db merge-candidates` 合并，并保留全部 Search Run provenance。`what_we_learned` 与 `next_decision` 记录这次检索如何改变下一步，而不是事后写成检索日志散文。

## 2. Candidate 默认进入全文队列

摘要只承担导航，不代表论文。完成 identity resolution 与 deduplication 后，除明显错误命中、非目标 scholarly work、重复记录等低成本可确认噪声外，相关 Candidate 默认进入全文获取与阅读队列。

摘要可以用于：

- 排除明显错误命中；
- 调整全文阅读优先级；
- 在写作阶段补充一个只需要摘要级背景的引用。

研究启动、问题发现、方法学习与证据综合阶段，不以“摘要看起来足够”作为结束条件。Candidate 的 `relevance_status`、`acquisition_status` 与 `reading_priority` 分开维护：相关性决定是否属于问题空间，获取状态说明全文是否已拿到，优先级只决定阅读顺序；`excluded` 必须留下明确 exclusion reason。相关 Candidate 默认进入 `queued` 全文获取队列，成功 `ingest-paper` 后自动回链正式 Paper。如何用标题/摘要/方法信号判断阅读价值、如何处理“摘要难懂但高度相关”的论文，以及稳定的人类 `literature/papers/` 阅读视图，统一按 [`READING-PROTOCOL.md`](READING-PROTOCOL.md) 执行；待读/已读不再通过目录移动表达。

`unavailable` 不是自由文本结论。每次正文获取尝试必须用 `research-db record-access-attempt` 持久化获取路径类别、资源类别、来源地址、实际结果和获取时间。对 `outcome=acquired` 还必须保存可审计的**获取依据（access basis）**，说明该全文属于出版社开放版本、公共/机构知识库、作者公开稿、预印本、用户认证访问或用户提供文件中的哪一种。一个互联网上可下载且身份匹配的 PDF 本身不足以证明它是可作为规范科研来源自动获取的全文；来源授权或开放依据无法核验时，不得用 `acquired` 闭合 Candidate，应继续正式开放路径或进入用户协同。检索运行（Search Run）不允许直接创建 `unavailable` Candidate；必须先进入待获取状态，实际调用 `literature-access`，记录失败/受限路径后再更新 Candidate。有 DOI 时至少检查出版社路径（publisher route）；同时至少有一个独立开放解析路径（open index / repository / preprint）。单一 PDF 的 403 或访问挑战不能闭合全文获取：必须继续检查出版社论文页面/网页全文以及解析器暴露的 PMCID、机构知识库或其他全文位置。

**机器侧拿不到全文时必须请求用户协同。** 对核心或高优先级相关论文，只要公开路径、普通 HTTP 或自动化资源解析仍不能取得正文，就进入用户协同访问：优先按 `literature-access → browser-access` 路由打开或复用用户可见的持久浏览器配置，由用户亲自完成其已有机构/订阅权限的登录、验证码或二次认证，再由智能体继续解析和取得全文；若用户能够从其有权使用的其他来源取得论文，则请求用户直接提供文件并重新做身份/完整性核验。Candidate 使用 `user_access_status` 与 `user_access_reason` 记录这一状态。只要 `user_access_status=required`，研究必须停在等待用户协同，不能标记 `unavailable`、不能宣称候选队列闭合，也不能通过完成门禁。只有用户明确完成协同仍无可用权限、无法提供合法副本，或者明确选择不继续协同，且机器侧获取来源也已闭合，才能把核心/高优先级论文记为当前 `unavailable`。

Acquisition Attempt 是不可覆盖的历史记录，但历史判断可以被**显式 supersede**。例如一开始把 subscription preview 误判成 `acquired`，后续完整边界核验发现并非全文时，新 attempt 必须通过 `supersedes_attempt_ids + supersession_reason` 结构化撤销旧判断；不得让一个仍为 active 的 `acquired` attempt 与 Candidate 的 `unavailable` 状态并存。`research-db discovery-status` 与 `validate` 会拒绝 provenance 不足或当前有效状态自相矛盾的 `unavailable`。

## 3. 全文获取与阅读深度

已知论文交给 `literature-access` 获取正文；浏览器只在需要登录、动态页面或真实资源请求解析时参与。正文、supplement、代码和数据仓库仍是独立 artifact，SQLite 记录论文身份、路径、版本、来源与获取时间。论文首次进入项目时使用 `research-db ingest-paper`，机器 canonical artifact 统一进入 `.research/artifacts/papers/<paper-id>/`；XML/HTML 等机器表示只保留在这里。若 Paper 已经存在、随后才取得 Supplementary Information、Source Data、代码/数据附件或新的正文表示，必须使用 `research-db add-paper-artifacts` 追加并登记 `artifacts` / `change_log`，不得重新 `ingest-paper`、直接写 SQL 或只手工放文件。人类 `literature/` 阅读区的目录、文件类型、命名与阅读顺序统一按 [`READING-PROTOCOL.md`](READING-PROTOCOL.md) 执行。若追加动作重新打开了既有阅读状态，继续完成对应的增量 Reconstruction 与 Critical Audit，直到当前 artifact 集合重新满足阅读门禁。

相关论文至少执行 `FULL_SCAN`：整篇正文过一遍并识别 research problem、design、methods、experiments、major observations、claims、limitations 与 leads。进入全文时先按 [`READING-PROTOCOL.md`](READING-PROTOCOL.md) 明确本次阅读目的；背景知识构建、前沿跟踪、方法学习、研究设计学习、证据核验和写作结构学习可以采用不同章节顺序，但最终 Reconstruction / Critical Audit 要求不变。研究设计与方法学习尤其要追踪前驱工作、代表实现、后续改进和边界条件，并在跨领域借鉴前核对关键假设能否迁移。`reading_priority=core` 且已成功获取的论文必须执行 `DEEP_EXTRACTION`；其他方法学上决定当前 Active Uncertainty 的论文即使未标 core，也应提升到 `DEEP_EXTRACTION`。深读继续覆盖 exact protocol、关键参数、supplement、统计细节、figure/table-level result、代码/数据仓库与关键引用链。`validate --completion` 会机械拒绝 `core + acquired` 仍停留在 `FULL_SCAN` 的状态。

深度抽取（DEEP_EXTRACTION）不是“读得比较认真”的主观标签。`ingest-reading` 必须持久化抽取检查（extraction checks）：确认观察结果（Observation）语义已经逐条自审、图表已检查、定量结果已检查，并明确记录补充材料（supplement）与代码/数据（code/data）的状态。补充材料必须记录 `supplement_presence = present | none_found | unclear`，代码/数据也必须对称记录 `code_data_presence = present | none_found | unclear`。只有经过正文和论文元数据检查确认没有相关线索时，才允许对应的 `none_found + not_applicable`；正文、数据可用性声明或页面元数据一旦明确给出附件、数据集、代码仓库或下载位置，就必须标记为 `present` 并继续实际获取/检查，不能用 `not_applicable` 跳过。无法取得时必须使用获取尝试（Acquisition Attempt）形成访问来源链。

只要数据库已经登记 supplement artifact，`artifacts_checked` 必须覆盖全部已取得附件，无论最终 `supplement_status` 是 `checked` 还是因其他缺失附件而 `access_limited`。`access_limited` 必须引用 `supplement_attempt_ids`，这些 ID 指向用 `research-db record-access-attempt` 保存的真实附件获取尝试；单一失败 endpoint 不足以构成 access limitation，必须继续替代 representation 或独立 route。若论文正文、PMC/Europe PMC、publisher article page 或其他已核验来源明确暴露 Supplementary Information / Source Data 的可访问链接，必须实际跟进，不能因尚未 ingest artifact 就把它写成 `access_limited`。Critical Audit 不能把仅完成 `FULL_SCAN` 的 Reconstruction 升级成 `DEEP_EXTRACTION`。若论文存在会影响当前证据判断的定量结果，所有进入核心 evidence chain 的 n、estimate/effect size、CI、P/FDR 等作者报告统计量必须进入对应 Observation 的 `statistics`；不能只把数字写在人类报告里而让结构化数据库保持空白。若确实没有相关定量结果，必须明确说明原因。

正文引用 Supplementary Methods、Supplementary Tables、protocol 或其他附件且它们影响当前研究时，必须继续检查；主文缺失但 supplement 尚未检查时，不得把信息标记成 `not_reported`。无法合法取得但会影响判断的 supplement 必须记录为 access limitation，不得默认为 `not_applicable`。

## 4. 两遍阅读协议

### Pass 1 — Reconstruction

第一遍忠实重建论文，不急于反驳作者。至少区分：

- `Method`：作者具体怎么做，包括关键 protocol、参数、材料、软件和可复用细节。
- `Experiment`：为了回答什么问题，采用什么 design、sample、group、control、measurement 与 analysis。
- `Observation`：数据直接显示了什么；不写作者解释，不用“支持”“证明”“有助于”替代实际结果。
- `Claim`：作者自己根据 observation 提出的 descriptive、association、causal、mechanistic 或 speculative statement。
- `Lead`：值得继续追的论文、方法、数据、代码、protocol、数据库或新问题。

Paper 保留稳定 `P000001` 一类 ID；论文内部知识单元由数据库主键管理，人类 sidecar 不暴露满屏缩写编号。

每个进入数据库的 Method、Experiment、Observation、Claim、Lead 都必须定位到具体 artifact，并给出可回到原文的 `source_locator`，优先精确到 subsection、page、figure/table/supplement item；仅有 `Methods`、`Results`、`Discussion`、`Abstract` 等顶层 section 名称或无来源定位不能视为完成 extraction，写入与 `validate` 都会拒绝这种模糊 locator。

Observation 与 Claim 强制分离。`Observation.statement` 与 `effect` 只承载图表、表格或正文能够直接复述的结果；`effect` 用于直接 contrast / effect size，bundle 的 `statistics` 保存作者报告的 n、estimate、CI、P/FDR 等具体统计量。对结果大小的意义、外部一致性、机制兼容性、缺失数据后果等解释进入 Claim、relation、Issue 或后续 synthesis。不得把 Agent 自己的解释写成作者 Claim。

写入前必须逐条执行 Observation semantic self-audit，并在 `extraction_checks.observation_semantics_checked=true` 后才能 ingest。判断标准是：“删掉论文作者和 Agent 的解释后，这句话是否仍然只是数据/图表/结果段可以直接复述的观察？”Method 操作（如 sample 被 surface sterilized）、作者自述限制（如 authors state direction cannot be determined）、Agent 批判（如 no longitudinal resilience test）以及“因此不能证明/支持/意味着”之类推论都不是 Observation，应分别进入 Method、Claim、Issue 或 relation。不能为了减少知识单元数量把不同语义层级压进一句 Observation。

### Evidence → Claim 关系必须说明“能支撑到哪一级”

不能因为一个 Observation 与某个 Claim 方向一致就机械写 `SUPPORTS`。至少区分：

- `DIRECTLY_SUPPORTS`：当前实验直接检验该层级 Claim，设计和 measurement 与 Claim 对齐。
- `INDIRECTLY_SUPPORTS`：方向一致，但存在物种、分类层级、代理指标、观察性设计或其他 inference gap；必须写 `note` 说明为什么只是间接支持。
- `QUALIFIES`：证据限定 Claim 的范围、机制或解释。
- `CONTRADICTS`：数据与 Claim 的明确预测相反；不能把单纯 `P > 0.05` 当作 contradiction。
- `DOES_NOT_TEST`：看似相关，但实际上没有检验该 Claim；必须写 `note`。

特别地：人类观察性关联不能直接建立人类因果结论；某一菌株在小鼠中的随机干预可以支持“该菌株在该小鼠模型中的因果效应”，但只能间接支持“人类某 genus/群落导致高原适应”这类跨物种、跨分类层级结论。

### Pass 2 — Critical Audit

第二遍以审稿人/竞争课题组视角主动攻击论文：寻找设计缺陷、证据断裂、替代解释、不可复现点和过度结论，而不是只抄作者的 limitations。

除了常规 design / statistics 检查，还特别警惕几类会制造“看起来有证据”的推理失败：只展示成功对象/成功算法/成功样本而忽略失败或未进入分析者；结果可见后改变 outcome、成功标准、group definition 或解释目标却仍按预设问题叙述；把群体/aggregate 层关系直接下放到 individual 层；缺少合理 base rate / comparator 却把高比例本身写成异常或效果；同一关键词在论证中悄然改变定义，或结论在前提中被循环假定。只有这些风险与当前论文实际结构相关时才记录 Issue，不为凑“逻辑谬误”标签制造批评。

至少检查：

- research question / hypothesis 是否清楚、可证伪，是否存在事后改题或 exploratory→confirmatory 包装；
- study design 的 confounding、selection bias、survivorship / success-only selection、batch confounding、pseudoreplication、control、non-independence、reverse causality；
- sampling 的独立 biological n、technical replicate、collection、storage、transport、freeze-thaw、contamination 与 metadata；
- assay / experimental method 的 specificity、sensitivity、control、calibration 与已知 bias；
- bioinformatics pipeline 的 QC、reference/database version、normalization、filtering、batch correction、参数敏感性、software version、random seed 与 data leakage；
- statistics 的 model/design 匹配、covariates、multiple testing、effect size、confidence interval、power、missing data、repeated measures、compositionality 与 overfitting；是否存在结果后改变 outcome / success criterion / subgroup definition 的 moving-target 问题；
- figures/tables 是否与正文表述一致，是否受 outlier、极小 effect、宽 CI 或可视化误导影响；
- Observation → Claim 是否出现 association→causation、mechanism leap、aggregate→individual 跨推断层级、缺少合理 comparator / base rate 的异常化叙事，或 unsupported narrative；
- alternative explanations 是否能同样解释结果；
- reproducibility 是否因参数、代码、数据、版本或 protocol 缺失而受限；
- Discussion 中哪些 statement 是 supported、plausible、overstated 或 unsupported；关键术语 / category definition 是否在 Methods、Results、Discussion 间发生会改变论证的语义漂移或循环定义。

作者自己声明的 limitation 与 Critical Audit 发现的问题必须分开。

每个 `Issue` 至少保存 category、nature、target、assessment、basis、`basis_rationale`、severity、confidence、why it matters、alternative explanation / possible resolution（若适用）以及具体 artifact + source locator。`basis_rationale` 必须说明为什么当前证据状态属于该 basis，而不是重复 assessment。

`nature` 描述问题是什么：

```text
flaw
scope_limitation
reporting_gap
concern
```

`basis` 取 `demonstrated | potential | not_reported`，回答当前判断的证据状态，而不是给问题贴价值标签。论文明确报告的样本量、研究设计、未采集来源、测量方法固有限制、已报告统计结果等已经成立的事实，原则上属于 `demonstrated`；`potential` 只用于尚未被数据或报告直接证实、但设计上真实存在的风险或替代解释；`not_reported` 只表示论文/附件没有报告所需信息，不能推断作者没有执行。每个 Issue 必须写 `basis_rationale` 明确这一步判断。`severity` 取 `critical | major | moderate | minor`；`confidence` 取 `high | medium | low`。例如“只研究年轻男性”可以是 `scope_limitation + demonstrated`，不应为了批判而称为 flaw。缺少报告也不等于证明没有执行，批判本身必须避免 overclaim。

只有完成 Reconstruction 与 Critical Audit，论文才可标记为 `critically_reviewed` 并进入后续跨论文综合。

## 5. 人类阅读输出

人类阅读输出统一按 [`READING-PROTOCOL.md`](READING-PROTOCOL.md) 生成。`literature/` 是人类阅读区，不是 raw artifact 仓库：论文的人类 Markdown 与可选 PDF 稳定放在 `literature/papers/` 根层，文件基础名采用“论文题名 - 第一作者 - 年份”；阅读优先级、Agent 阅读状态和用户本人是否确认当前版本都由数据库/Git provenance 表达，不再使用 `to-read/read` 目录移动。主题/状态集合使用 `literature/collections/*.md` 作为索引，不另建 `*_must_read/` 目录复制论文。

新生成或由 Agent 实质重写的人类 Markdown 使用 [`READING-PROTOCOL.md`](READING-PROTOCOL.md) 定义的 `akira:literature-note:v1` 固定格式：唯一一级标题为原始论文题名，随后是固定书目信息表；正文固定使用“三句话总结 → 为什么值得读 → 论文逻辑 → 方法拆解 → 实验逻辑 → 数据直接显示 → 作者解释 → 我们的证据评估 → 关键图表与定位 → 可复用内容 → 科研启发 → 结论边界 → 我的笔记”的 `##` 二级标题顺序，`###` 及更深层标题按论文类型自由展开。sidecar 不做逐段摘要，只保留能快速恢复理解和支持下一次科研决策的高价值综合。顶部和结尾各保留一个标准“我已阅读并确认当前版本”复选框；两者是同一用户确认状态的入口，使用 `research-db sync-user-reading` 同步。文末 `akira:user-notes` 是用户专属区块：Agent 只初始化边界，之后逐字保留，不修改、整理或总结其中内容；该区块不参与阅读确认 content OID，因此用户自己补写笔记不会使确认失效。Agent 更新自己的阅读正文时不得把旧 `[x]` 当成用户对新版本的确认；同步器发现 Agent 正文版本变化会使旧确认失效并清空复选框。用户确认与 Agent Reconstruction/Critical Audit 分开，不作为 Literature completion 条件。数据库保存完整结构化 extraction，sidecar 只保存高价值、可快速恢复理解的人类综合。

## 6. 科研结论的 Evidence Gate

任何由 Agent 给出的项目级科研结论都必须能追溯到明确论文，而不是来自模型常识或无引用综合。进入结论前依次回答：

1. 哪些 Paper（Paper ID + DOI/PMID）提供证据？
2. 每篇 Paper 的哪些 Observation 是直接数据？
3. 这些 Observation 与目标 Claim 是 `DIRECTLY_SUPPORTS`、`INDIRECTLY_SUPPORTS`、`QUALIFIES`、`CONTRADICTS` 还是 `DOES_NOT_TEST`？
4. Claim 层级是 descriptive、association、causal 还是 mechanistic；证据是否真的达到同一层级？
5. Critical Audit 中哪些 Issue 会降低该证据的 directness、scope 或 confidence？
6. 支持证据与反证/边界条件都考虑后，最窄、最可辩护的结论是什么？

没有明确 supporting Paper 或无法说明 evidence-to-claim fit 时，结论保持 `UNRESOLVED`，不能由模型补齐。

## 7. 跨论文证据综合

Evidence Map 不再人工维护为大量 Markdown，而是由 SQLite 中的 Observation、Claim、Issue、Paper 关系动态生成。综合时：

- 以 Claim / Evidence 为单位，不以 Paper 数量投票；
- 描述、关联、因果、机制 Claim 分开；
- 共享 cohort、sample 或 dataset 的论文不视为独立 replication，使用 relation 标记并在查询时聚合；
- Critical Audit 必须影响 evidence strength；
- `P > 0.05` 不自动等于 contradiction，除非 design、power 与区间足以支持 absence；
- 对矛盾主动寻找 population、exposure duration、diet、platform、preservation、analysis pipeline、definition 等 heterogeneity / boundary condition；
- Research Gap 优先来自 unresolved contradiction、untested alternative、missing control、missing population / temporal scale、measurement limitation 或 unvalidated mechanism，而不是简单“研究较少”。

证据视图由脚本检索和展开关系，主模型负责科学解释；脚本不得用硬编码评分替代 evidence-to-claim 判断。

主题型 Literature Discovery 在形成项目级综合时，关键的跨论文判断也必须进入 canonical relation graph，而不能只存在 derived synthesis Markdown。至少把真正改变项目判断的跨论文 `INDIRECTLY_SUPPORTS / QUALIFIES / CONTRADICTS / DOES_NOT_TEST / LIMITS / CHALLENGES / WEAKENS` 等关系落库，并在 `note` 中说明 inference gap 或限定。`SHARES_SAMPLES_WITH`、`SHARES_DATA_WITH` 与 `CITES` 只描述来源关系，不能替代跨论文 Evidence Synthesis。已有至少两篇完成 Critical Audit 的论文、且执行了主题型 Discovery 时，`validate --completion` 要求至少存在一条跨不同 Paper 的 scientific relation。

Literature Research 完成后，必须把真正改变项目判断的新 evidence、最重要的 `unresolved`、仍存的竞争解释与最有判别力的下一条证据写入同一个项目的 canonical sources；值得持续追踪的新猜想同时保留正确 proposal provenance。`RESEARCH.md` 只接收仍然影响当前路线的高层变化，不能变成文献日志。

Literature completion 只表示本轮文献发现、获取、阅读、批判和综合已经闭合；它不意味着整个科研 Objective 已经解决，也不构成机械进入 `HYPOTHESIS` 或 `DESIGN` 的理由。准备结束完整 Literature Research 前，按当前模式做最后检查：`DISCOVERY` 检查 `discovery-status`、适用的 acquisition / reading / Critical Audit / cross-paper relation、canonical state、Git 状态与 `validate --completion` 的共享 readiness；`SYSTEMATIC` 则检查 frozen protocol、全部 protocol-bound Search Runs、deduplication、screening / full-text exclusion、extraction、适用 appraisal、Data / Analysis / Interpretation 交接和 final search 状态，再运行共享 `validate --completion`。其中任何本工作流未闭合项若不是前述真实外部 blocker，就继续执行而不是返回阶段总结。不要要求与本轮 Literature 无关的其他科研工作流同时完成。

只有达到 `COMPLETED` 后才把控制权交回 `akira-research`，由更新后的 Scientific State 重新选择下一动作：现有项目数据已经能取得判别性证据时应进入 `ANALYSIS`；需要把竞争解释转成不同预测时进入 `HYPOTHESIS`；确实需要新的 sampling、measurement 或 intervention 时才进入 `DESIGN`。若状态为 `BLOCKED`，控制权停在当前 Literature work，并把解除 blocker 作为项目下一条真实 `Active Work`。Literature Skill 不另行维护一套项目路线或最终科学结论。
