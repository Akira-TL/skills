# Literature Protocol

本文件定义 `ask-akira-research` 的文献发现、全文阅读、批判审阅与跨论文证据综合。已知目标论文的合法全文获取由 `literature-access` 负责；本文件负责决定为什么找、哪些论文进入队列、读什么、如何批判以及如何把结果写入研究知识库。

## 1. Discovery，不把日常科研伪装成 Systematic Review

默认模式为 `DISCOVERY`：目标是高召回地理解领域、发现术语、方法、矛盾、边界条件与关键工作。检索式允许迭代；每次检索作为独立 Search Run 写入数据库，保留 purpose、source、query、filters、parent run、reason、result count、what we learned 与 next decision。

只有用户明确需要 systematic review、meta-analysis、scoping review 或可发表的正式系统检索时才进入 `SYSTEMATIC`；该模式的完整 protocol 另行设计，不用 discovery 规则冒充系统综述。

Discovery 采用循环：

```text
Active Uncertainty
→ seed search
→ terminology / author / method learning
→ query expansion
→ backward / forward citation chasing
→ related-work search
→ new search run
→ conceptual saturation
```

搜索停止依据是相对当前 Active Uncertainty 的边际知识增益：连续检索与引用追踪不再产生新的重要方法、观察、解释、矛盾、边界条件、研究设计或基础工作时，可以认为 discovery 达到当前目的的 saturation；不以固定论文数量作为停止条件。

在正式声称 practical conceptual saturation 前必须运行 `research-db discovery-status`。`core + relevant` Candidate 必须已经 `acquired` 或明确 `unavailable`；`high + relevant` Candidate 若仍处于 `pending/queued`，必须保存具体 `defer_reason` 说明为什么它预计不会改变当前 Active Uncertainty / Evidence Boundary；`relevance_status=pending` 不能遗留；稳定 DOI/PMID 重复必须先合并。工具返回 `ready_for_saturation=false` 时不得仅凭主观判断宣布 saturation。

每次真实搜索结束后用 `research-db record-search` 原子持久化 Search Run 与本次保留的 Candidate；同一论文在 seed search、query expansion 与 citation chasing 中重复出现时应复用 Candidate，并保留每个 `search_run_candidates` 发现边。identity resolution 只改变同一 scholarly work 的身份信息，不应通过 `excluded` 制造“重复论文”记录；发现旧 Candidate 与新稳定 DOI/PMID 实际属于同一 scholarly work 时，用 `research-db merge-candidates` 合并，并保留全部 Search Run provenance。`what_we_learned` 与 `next_decision` 记录这次检索如何改变下一步，而不是事后写成检索日志散文。

## 2. Candidate 默认进入全文队列

摘要只承担导航，不代表论文。完成 identity resolution 与 deduplication 后，除明显错误命中、非目标 scholarly work、重复记录等低成本可确认噪声外，相关 Candidate 默认进入全文获取与阅读队列。

摘要可以用于：

- 排除明显错误命中；
- 调整全文阅读优先级；
- 在写作阶段补充一个只需要摘要级背景的引用。

研究启动、问题发现、方法学习与证据综合阶段，不以“摘要看起来足够”作为结束条件。Candidate 的 `relevance_status`、`acquisition_status` 与 `reading_priority` 分开维护：相关性决定是否属于问题空间，获取状态说明全文是否已拿到，优先级只决定阅读顺序；`excluded` 必须留下明确 exclusion reason。相关 Candidate 默认进入 `queued` 全文获取队列，成功 `ingest-paper` 后自动回链正式 Paper。

## 3. 全文获取与阅读深度

已知论文交给 `literature-access` 获取正文；浏览器只在需要登录、动态页面或真实资源请求解析时参与。正文、supplement、代码和数据仓库仍是独立 artifact，SQLite 记录论文身份、路径、版本、来源与获取时间。

相关论文至少执行 `FULL_SCAN`：整篇正文过一遍并识别 research problem、design、methods、experiments、major observations、claims、limitations 与 leads。核心或方法学重要论文执行 `DEEP_EXTRACTION`：继续深入 exact protocol、关键参数、supplement、统计细节、figure/table-level result、代码/数据仓库与关键引用链。

`DEEP_EXTRACTION` 不是“读得比较认真”的主观标签。`ingest-reading` 必须持久化 `extraction_checks`：确认 Observation 语义已经逐条自审、figures/tables 已检查、定量结果已检查，并明确记录 supplement 与 code/data 的状态为 `checked | not_applicable | access_limited`。若论文存在会影响当前证据判断的定量结果，所有进入核心 evidence chain 的 n、estimate/effect size、CI、P/FDR 等作者报告统计量必须进入对应 Observation 的 `statistics`；不能只把数字写在人类报告里而让结构化数据库保持空白。若确实没有相关定量结果，必须明确说明原因。

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

每个进入数据库的 Method、Experiment、Observation、Claim、Lead 都必须定位到具体 artifact，并给出可回到原文的 `source_locator`，优先精确到 section + figure/table/supplement；仅有模糊的“Results”或无来源定位不能视为完成 extraction。

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

至少检查：

- research question / hypothesis 是否清楚、可证伪，是否存在事后改题或 exploratory→confirmatory 包装；
- study design 的 confounding、selection bias、batch confounding、pseudoreplication、control、non-independence、reverse causality；
- sampling 的独立 biological n、technical replicate、collection、storage、transport、freeze-thaw、contamination 与 metadata；
- assay / experimental method 的 specificity、sensitivity、control、calibration 与已知 bias；
- bioinformatics pipeline 的 QC、reference/database version、normalization、filtering、batch correction、参数敏感性、software version、random seed 与 data leakage；
- statistics 的 model/design 匹配、covariates、multiple testing、effect size、confidence interval、power、missing data、repeated measures、compositionality 与 overfitting；
- figures/tables 是否与正文表述一致，是否受 outlier、极小 effect、宽 CI 或可视化误导影响；
- Observation → Claim 是否出现 association→causation、mechanism leap 或 unsupported narrative；
- alternative explanations 是否能同样解释结果；
- reproducibility 是否因参数、代码、数据、版本或 protocol 缺失而受限；
- Discussion 中哪些 statement 是 supported、plausible、overstated 或 unsupported。

作者自己声明的 limitation 与 Critical Audit 发现的问题必须分开。

每个 `Issue` 至少保存 category、nature、target、assessment、basis、severity、confidence、why it matters、alternative explanation / possible resolution（若适用）以及具体 artifact + source locator。

`nature` 描述问题是什么：

```text
flaw
scope_limitation
reporting_gap
concern
```

`basis` 取 `demonstrated | potential | not_reported`，回答当前判断的证据状态，而不是给问题贴价值标签。`severity` 取 `critical | major | moderate | minor`；`confidence` 取 `high | medium | low`。例如“只研究年轻男性”可以是 `scope_limitation + demonstrated`，不应为了批判而称为 flaw。缺少报告也不等于证明没有执行，批判本身必须避免 overclaim。

只有完成 Reconstruction 与 Critical Audit，论文才可标记为 `critically_reviewed` 并进入后续跨论文综合。

## 5. 人类 sidecar

每篇下载论文旁边保留一份短小的人类必读 sidecar，例如 `README.md`。它是精简视图，不是数据库 dump。目标是在 1–3 分钟内让用户恢复“为什么保存这篇、数据真正显示什么、作者怎么解释、哪里有问题、我们能学什么”。

推荐结构：

```text
Source
Why It Matters
What They Did
What The Data Directly Show
What The Authors Claim
Our Evidence Assessment
What We Can Reuse
What Is Wrong / Uncertain
Bottom Line
```

`Bottom Line` 必须把“论文直接支持什么”和“尚未建立什么”分开，不用“强烈支持某因果结论”概括一个主要由观察性人群数据加跨物种动物实验组成的证据链。

数据库保存尽可能完整的结构化 extraction；sidecar 只保留高价值 synthesis。

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
