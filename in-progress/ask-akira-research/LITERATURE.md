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

## 2. Candidate 默认进入全文队列

摘要只承担导航，不代表论文。完成 identity resolution 与 deduplication 后，除明显错误命中、非目标 scholarly work、重复记录等低成本可确认噪声外，相关 Candidate 默认进入全文获取与阅读队列。

摘要可以用于：

- 排除明显错误命中；
- 调整全文阅读优先级；
- 在写作阶段补充一个只需要摘要级背景的引用。

研究启动、问题发现、方法学习与证据综合阶段，不以“摘要看起来足够”作为结束条件。

## 3. 全文获取与阅读深度

已知论文交给 `literature-access` 获取正文；浏览器只在需要登录、动态页面或真实资源请求解析时参与。正文、supplement、代码和数据仓库仍是独立 artifact，SQLite 只记录 canonical path、版本、来源、来源 URL 与获取时间；论文身份优先由 DOI / PMID / PMCID 等稳定标识确认，不为日常文献入库计算内容 hash。

相关论文至少执行 `FULL_SCAN`：整篇正文过一遍并识别 research problem、design、methods、experiments、major observations、claims、limitations 与 leads。核心或方法学重要论文执行 `DEEP_EXTRACTION`：继续深入 exact protocol、关键参数、supplement、统计细节、figure/table-level result、代码/数据仓库与关键引用链。

正文引用 Supplementary Methods、Supplementary Tables、protocol 或其他附件且它们影响当前研究时，必须继续检查；主文缺失但 supplement 尚未检查时，不得把信息标记成 `not_reported`。

## 4. 两遍阅读协议

### Pass 1 — Reconstruction

第一遍忠实重建论文，不急于反驳作者。至少区分以下知识类型，正文使用完整类型名，不要求用户记忆字母缩写：

- `Method`：作者具体怎么做，包括关键 protocol、参数、材料、软件和可复用细节。
- `Experiment`：为了回答什么问题，采用什么 design、sample、group、control、measurement 与 analysis。
- `Observation`：数据直接观察到了什么；与作者解释分开。
- `Claim`：作者基于 observation 提出的 descriptive、association、causal、mechanistic 或 speculative statement。
- `Lead`：值得继续追的论文、方法、数据、代码、protocol、数据库或新问题。

Paper 保留稳定 `P000001` 一类 ID；论文内部知识单元由数据库主键管理，人类 sidecar 不暴露满屏缩写编号。

每个重要知识单元必须能够回到原文，记录可得的 artifact、section、page、figure/table 等 source locator。Observation 与 Claim 强制分离；Claim 应通过 relation 指向支持或削弱它的 Observation。

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

每个 `Issue` 至少保存 category、nature、target、assessment、basis、severity、confidence、why it matters、alternative explanation / possible resolution（若适用）以及 source locator。

`nature` 取：

- `flaw`：设计、执行、分析或推理中存在会削弱结论的实际缺陷；
- `scope_limitation`：研究本身可以成立，但证据外推范围受到 population、时间尺度、实验条件等明确边界限制；
- `reporting_gap`：关键过程或参数在检查正文、supplement 与被引用 protocol 后仍未报告；
- `concern`：有合理风险需要继续核查，但当前材料不足以归入以上更确定类别。

`basis` 取 `demonstrated | potential | not_reported`，回答当前判断的证据状态，而不是给问题贴价值标签。`severity` 取 `critical | major | moderate | minor`；`confidence` 取 `high | medium | low`。例如“只研究年轻男性”可以是 `scope_limitation + demonstrated`，不应为了批判而称为 flaw。缺少报告也不等于证明没有执行，批判本身必须避免 overclaim。

只有完成 Reconstruction 与 Critical Audit，论文才可标记为 `critically_reviewed` 并进入后续跨论文综合。

## 5. 人类 sidecar

每篇下载论文旁边保留一份短小的人类必读 sidecar，例如 `README.md`。它是精简视图，不是数据库 dump。目标是在 1–3 分钟内让用户恢复“为什么保存这篇、做了什么、发现什么、哪里有问题、我们能学什么”。

建议包含：

```text
Why It Matters
What They Did
What They Found
What We Can Reuse
What Is Wrong / Uncertain
Innovation
Bottom Line
```

数据库保存尽可能完整的结构化 extraction；sidecar 只保留高价值 synthesis。

## 6. 跨论文证据综合

Evidence Map 不再人工维护为大量 Markdown，而是由 SQLite 中的 Observation、Claim、Issue、Paper 关系动态生成。综合时：

- 以 Claim / Evidence 为单位，不以 Paper 数量投票；
- 描述、关联、因果、机制 Claim 分开；
- 共享 cohort、sample 或 dataset 的论文不视为独立 replication，使用 relation 标记并在查询时聚合；
- Critical Audit 必须影响 evidence strength；
- `P > 0.05` 不自动等于 contradiction，除非 design、power 与区间足以支持 absence；
- 对矛盾主动寻找 population、exposure duration、diet、platform、preservation、analysis pipeline、definition 等 heterogeneity / boundary condition；
- Research Gap 优先来自 unresolved contradiction、untested alternative、missing control、missing population / temporal scale、measurement limitation 或 unvalidated mechanism，而不是简单“研究较少”。

证据视图由脚本检索和展开关系，Agent 负责科学解释；不要在脚本中硬编码伪精确的自动 evidence score。
