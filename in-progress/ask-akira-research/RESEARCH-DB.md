# Research SQLite Contract

本文件定义 `ask-akira-research` 的项目级科研知识数据库契约。当前已实现 schema migration、`init`、`migrate`、`ingest-paper`、`ingest-reading`、`ingest-critical`、`status`、`validate`、FTS 检索与 `evidence` 查询。

## 1. Source of truth

项目中的三类内容职责分开：

- `RESEARCH.md`：当前研究状态与路线的 canonical source。
- `.research/research.sqlite`：详细结构化科研知识的 canonical source，并进入 Git 保存版本快照。
- PDF、supplement、代码、数据等原始 artifact：保持为独立文件；数据库只记录路径、版本、来源、来源 URL 与获取时间，不保存 blob。论文身份优先由 DOI / PMID / PMCID 等稳定标识确认，不为日常文献入库计算内容 hash。

每篇已下载论文旁边保留精简的人类 sidecar；sidecar 是给用户阅读的 synthesis，不复制数据库的完整 extraction，也不作为详细知识的 canonical source。

PDF 的长期 artifact storage / Git 策略仍是独立设计问题；本契约只要求数据库能够通过 Paper identity + path + provenance 回到对应文件。

## 2. 数据库边界

一个科研项目只维护一个 `research.sqlite`。当前 schema 只建立真正需要的表：

```text
meta
papers
artifacts
search_runs
candidates
acquisition_attempts
reading_runs
methods
experiments
observations
claims
issues
leads
relations
change_log
datasets
dataset_artifacts
analysis_runs
analysis_inputs
analysis_dataset_artifact_timing
analysis_artifacts
analysis_amendments
project_observations
hypothesis_sets
research_designs
hypothesis_evaluations
communication_products
communication_artifacts
```

暂不建立独立 evidence graph、method graph、evidence family 或 contradiction Markdown / tables；能够从现有节点与关系动态查询得到的视图先不物化。未来只有出现稳定的独立领域对象时再通过 migration 增加表。

## 3. 查询层：Search 与 Evidence

查询层只负责从 canonical source 提取可追溯证据单元，不替代科研判断。

- `search`：信息发现，返回匹配的 Paper / Method / Observation / Claim / Issue。
- `evidence`：证据包，返回相关 Claim、Observation、Issue 与 relations，并保留 artifact locator。
- `evidence` 不输出证据强弱评分，不自动生成结论；DIRECTLY_SUPPORTS、QUALIFIES 等关系仍需要由主模型结合研究问题解释。

例如：

```bash
research-db evidence "hypoxia gut microbiome adaptation"
```

输出可作为 Evidence Synthesis 的输入，而不是最终科研结论。

## 4. 核心表

### `meta`

至少保存 `schema_version`。从 v1 起所有 schema 演化通过 migration 完成，不允许依赖手工、不可追踪的 `ALTER TABLE`。

### `papers`

保存论文身份与总体阅读状态：

```text
id                  -- P000001
title
doi
pmid
pmcid
authors             -- JSON
journal
year
paper_type
canonical_identity
status
read_depth
reading_status
critical_status
sidecar_path
created_at
updated_at
```

建议状态：

```text
status: discovered | acquired | active | archived
read_depth: none | full_scan | deep_extraction
reading_status: unread | reconstructed | extracted
critical_status: not_reviewed | critically_reviewed
```

Paper ID 可以对人稳定暴露；Method、Observation、Issue 等内部实体使用数据库主键，不要求用户记忆字母缩写。

### `artifacts`

保存文件索引而不是文件内容：

```text
id
paper_id
kind
path
content_type
version
source
source_url
retrieved_at
created_at
```

`kind` 可表示 `main_text`、`supplementary_methods`、`supplementary_table`、`supplementary_figure` 等。

### `search_runs`

每次真实检索作为独立记录，不覆盖旧 query：

```text
id
purpose
mode
source
query
filters
parent_run_id
reason
executed_at
result_count
what_we_learned
next_decision
discovery_method      -- seed_search | query_expansion | backward_citation | forward_citation | related_work | method_search | update_search | exact_work | other
```

### `candidates`

保存搜索发现层与正式 Paper 之间的 identity / deduplication provenance：

```text
id
title
doi
pmid
authors
year
discovery_source
source_url
identity_status        -- unresolved | resolved
relevance_status       -- pending | relevant | excluded
relevance_reason
acquisition_status     -- pending | queued | acquired | unavailable
reading_priority       -- core | high | normal | low
exclusion_reason
defer_reason            -- normal/low Candidate 的延期说明；不能用于 core/high 闭合
user_access_status      -- not_required | required | completed | declined | unavailable_to_user
user_access_reason      -- 为什么需要/结束用户协同访问
paper_id
created_at
updated_at
```

同一 Candidate 可以由多次 Search Run 独立发现；`search_run_candidates` 保存 `search_run_id + candidate_id + result_rank + source_result_id/source_url`，避免把重复发现误当独立论文。DOI/PMID 已解析时优先按稳定身份复用 Candidate；没有稳定身份时对规范化后的 title/year 做保守 identity enrichment，以吸收标点、大小写和连字符差异。发现历史上已经存在的重复 Candidate 时使用 `research-db merge-candidates`，把 Search Run provenance 合并到一条 canonical Candidate；不要用 `relevance_status=excluded` 代替 identity reconciliation。论文经 `ingest-paper` 获取后，匹配 Candidate 自动回链 `paper_id` 并更新为 `acquired`。

Candidate ID 主要供数据库内部使用。

### 项目自身数据与分析

从 schema v13 起，项目自身的数据与分析不再只存在于 Markdown/Git 中；数据库保存最小、稳定的 provenance 对象，而文件仍保持为独立 artifact。

`datasets` 保存数据集身份、来源、版本、接收时间、独立推断单位与人类可读 provenance 路径。`dataset_artifacts` 保存 raw / curated / metadata / manifest 等位置；大型或受控数据允许 `storage_kind=external`，本地文件若不要求 Git 跟踪必须明确 `tracking_reason`。从 schema v17 起，`analysis_dataset_artifact_timing` 保存 Analysis 与 canonical Dataset artifact 的时序关系。默认没有关系记录时，该 Analysis 所连接 Dataset 的全部 local + `git_tracking=required` artifact 都属于 pre-result freeze；只有结果可见后才新增、且未参与该 Analysis 输入/执行的来源或测量 provenance，才显式登记 `timing_role=post_result_context` 与 `reason`。这不会把文件移出 Dataset 或 canonical Git provenance，也无需把它伪装成 Analysis result；关系只作用于指定 Analysis，后续 Analysis 默认重新纳入新的 freeze scope。

`analysis_runs` 保存一个可独立解释的分析动作：当前不确定性、估计目标（estimand / target contrast）、独立推断单位、主要分析、分析入口、可重放代码和状态。确认性分析（confirmatory analysis）在进入 `frozen/completed` 时必须记录结果可见前的 `freeze_commit`；一旦进入 frozen/completed，该 freeze pointer 不得被后续调用替换。Analysis 首次进入 `completed` 时固定 `completed_at`，后续仅追加 artifact、amendment、Observation 或 provenance relation 时保留原完成时间；显式传入冲突时间应拒绝，而不是覆盖或静默重记。从 schema v15 起，Analysis 如果实现已登记的 Research Design，还通过 `design_id` / `design_slug` 建立显式连接；不能只依靠重复的 estimand 文本形成隐式对应。

`analysis_inputs` 连接 Analysis 与 Dataset；`analysis_artifacts` 保存 estimate、diagnostic、figure、table、log、附加代码/报告等文件，并用 `timing_role=pre_result_support|result` 区分结果前必须已经存在的支持 artifact 与真正由分析产生的结果 artifact；`analysis_amendments` 区分 `pre_result` 与 `post_result` 的分析修改；`project_observations` 保存由项目自身分析直接得到的 Observation，并必须指向具体 Analysis artifact。它与论文绑定的 `observations` 分开，不能用后者伪装项目自己的结果。

`research-db validate --completion` 会把已登记且需要 Git 跟踪的 data/analysis artifact 纳入 canonical path gate。`data/` 或 `analysis/` 下已经被 Git 跟踪但没有进入上述 provenance 的文件会阻止完成；实际生成 curated 数据、主要结果、敏感性结果或关键诊断的项目脚本即使位于 `scripts/`，也应作为 Dataset / Analysis artifact 登记，从而进入同一 canonical Git gate。已完成的确认性 Analysis 还必须证明其 freeze commit 是当前 HEAD 的祖先、主要计划/代码/输入以及未被该 Analysis 标为 `post_result_context` 的 canonical Dataset artifact 在 freeze 时已经存在，并且这些路径在 `freeze_commit..HEAD` 的提交历史中从未被改写；中间改写后再 revert 也不能恢复原 freeze 资格。本轮结果 artifact 在 freeze 时必须尚不存在。`post_result_context` artifact 仍进入 canonical Git gate；completion 要求它在该 Analysis 的 freeze 时不存在，且它首次进入 Git 历史的提交中已经存在当前 Analysis 的至少一个已登记 result artifact，防止把仅仅“晚于 freeze”但实际早于结果的 provenance 事后洗成 post-result context。

从 schema v14 起，Hypothesis Set 与 Research Design 经过真实设计黑盒后已经显示出稳定的身份与冻结审计需求，因此进入最小结构化 provenance：`hypothesis_sets` 保存 target uncertainty、canonical `hypotheses/<slug>.md`、**artifact 生命周期状态**与 freeze commit；`research_designs` 保存关联 Hypothesis Set、主要 estimand、primary outcome、experimental unit、canonical `designs/<slug>.md`、feasibility 状态与 freeze commit。`hypothesis_sets.status=frozen` 表示结果前版本被冻结，不等于科学上“假设已确认”。

从 schema v15 起，完整的 pre-data → Analysis → Interpretation 黑盒进一步稳定暴露出 `hypothesis_evaluations`：一次 Evaluation 连接一个 Hypothesis Set、一个 completed Analysis 和该 Analysis 已登记的具体解释/结果 artifact，并记录本轮总体判别为 `unresolved | partially_resolved | resolved | not_interpretable`、decision、summary 与时间。Evaluation 是追加式科研事件，同一 Hypothesis Set 可以被后续不同 Analysis 继续产生新的 Evaluation；同一 Analysis 对同一 Hypothesis Set 的评价不可覆盖。这样保存证据更新历史，而不把“最新科学状态”错误塞进 Hypothesis Set 的 freeze 生命周期字段。

从 schema v16 起，科研传播黑盒进一步稳定暴露出 `communication_products` 与 `communication_artifacts`。Communication Product 只保存传播目标、受众、状态以及传播开始前的 `source_commit`；artifact 保存题目/摘要、方法、结果、讨论、图、图注、大众摘要、追溯文件和生成脚本等路径，并用 `timing_role=source_support|derived_output` 约束其相对 source commit 的时序。传播文件进入 Git 完整性门禁，但它们仍是 canonical scientific evidence 的派生输出，不会因为进入数据库而成为第四类科研事实源。

完成的 Communication Product 会检查 `source_commit` 是否真实存在并属于当前历史、派生产物是否晚于 source commit，以及 source commit 后 Hypothesis / Design / Data / Analysis 等已登记科学 artifact 是否又发生变化。若科学源发生变化，传播稿必须基于新的稳定 evidence commit 重新审阅。该门禁可以审计版本关系，却不能自动判断一句标题或 Discussion Claim 是否在语义上过强；这种科研语义仍由主模型审查。

数据库**不**复制每个 H1/H2、Prediction、Discriminator Matrix、Decision Boundary、传播稿逐句 Claim、组别表、单个 hypothesis 的 `live/favored/weakened/...` 状态或完整设计正文；这些仍由 canonical Markdown artifact 或派生传播文件承载。当前也不建立 Project Claim / Communication Claim 表。只有未来真实项目反复证明某个科研语义对象存在稳定的跨项目查询/关系需求时，才继续迁移，不能为了工作流阶段对称而机械建表。

### `acquisition_attempts`

保存正文、Supplementary Information 与 code/data 的真实获取尝试，用来区分“某个 URL 请求失败”与“当前合法获取路径已经合理穷尽”：

```text
id
candidate_id          -- 正文 Candidate 获取时使用
paper_id              -- 已入库论文的 supplement/code-data 获取时使用
target_kind           -- main_text | supplement | code_data
target_label          -- attachment target 的具体名称/编号
route_family          -- publisher | open_index | repository | preprint | authenticated | other
resource_kind         -- article_page | full_text_html | pdf | xml | repository_record | supplement | other
source_url
outcome               -- acquired | not_found | access_denied | auth_required | challenge | invalid_artifact | network_error | other_failure
detail
attempted_at
access_basis          -- not_applicable | publisher_open | public_repository | institutional_repository | author_manuscript | preprint | authenticated_user | user_provided | unverified
access_basis_detail   -- 为什么该全文具有明确开放、授权或用户提供依据
validity_status        -- active | superseded
superseded_by_attempt_id
supersession_reason
```

Candidate 不允许在检索运行（Search Run）中直接创建为 `unavailable`。正文获取失败后先 `record-access-attempt`，再由 `update-candidate` 执行闭合：有 DOI 时必须留下出版社（publisher）获取尝试，同时必须有独立开放解析路径；单一被拒绝的出版社 PDF 还必须检查出版社论文页面/网页全文。核心或高优先级相关论文在机器侧路径失败后必须继续请求用户协同：`user_access_status=required` 表示等待用户在持久可见浏览器中完成已有权限的登录/认证，或等待用户提供全文文件。该状态不能转成 `unavailable`，也不能通过文献发现闭合门禁。只有用户协同已经完成仍无可用全文、用户确认自己没有可用权限，或用户明确选择不继续协同，并且机器侧来源也闭合，才允许把核心/高优先级论文记录为当前 `unavailable`。

`outcome=acquired` 同样需要可审计来源依据。正文获取记录必须有可接受的 `access_basis`；来源不明的普通网络镜像不能因为“文件能下载且 DOI 匹配”就闭合为正式全文。出版社开放全文、公共或机构知识库、作者公开稿、正式预印本、用户认证访问以及用户直接提供的全文均可形成合格获取依据；无法确认来源依据时保持 `unverified` 并继续正式开放路径或用户协同。

Attempt 历史不可覆盖。后续核验若发现某条旧 attempt 的 `outcome` 判断错误，新 attempt 使用 `supersedes_attempt_ids` 和强制 `supersession_reason` 把旧记录标记为 `superseded`；旧记录仍保留，但不再参与当前 access closure。`unavailable` Candidate 不允许存在仍为 `active` 的 `outcome=acquired` attempt。

### `reading_runs`

证明 Reconstruction 与 Critical Audit 实际执行过：

```text
id
paper_id
pass                -- reconstruction | critical_audit
depth               -- full_scan | deep_extraction
started_at
completed_at
artifacts_checked    -- JSON
sections_checked     -- JSON
notes
extraction_checks_json -- Observation 语义自审、定量结果、figures/tables、supplement、code/data 检查状态及不适用/访问受限理由
```

不能只靠手工修改 `papers.critical_status` 冒充完成批判阅读。

### `methods`

```text
id
paper_id
name
purpose
description
parameters          -- JSON / text
materials           -- JSON / text
software            -- JSON / text
reusable_notes
artifact_id
source_locator
```

### `experiments`

```text
id
paper_id
question
design
samples
groups_json
controls
variables_json
analysis
result_summary
artifact_id
source_locator
```

`result_summary` 只用于导航；真正数据结果进入 `observations`。

### `observations`

```text
id
paper_id
experiment_id
statement
effect              -- 数据直接报告的 contrast / effect size，不承载 Agent 解释
statistics_json     -- n / estimate / CI / P / FDR 等作者报告的具体统计量
scope
certainty
artifact_id
source_locator
```

Observation 只记录数据直接显示的内容，不混入 Method 操作、作者限制、Agent 批判或证据解释。`ingest-reading` 要求 `extraction_checks.observation_semantics_checked=true`；`deep_extraction` 还要求显式完成 figures/tables、quantitative results、supplement 与 code/data 检查。Supplement 必须另外记录 `supplement_presence=present|none_found|unclear`；`access_limited` 必须引用已持久化的失败 Acquisition Attempt，且不能由一个失败 endpoint 构成。若 `quantitative_results_present=true`，至少一个 Observation 必须保存非空 `statistics_json`；真正影响核心 evidence chain 的作者报告定量结果不能只存在于 derived report。

### `claims`

```text
id
paper_id
statement
claim_type
author_strength
scope
artifact_id
source_locator
```

`claim_type`：`descriptive | association | causal | mechanistic | speculative`。

### `issues`

保存第二遍 Critical Audit 的结构化批判：

```text
id
paper_id
category
nature
target_type
target_id
assessment
basis
basis_rationale
severity
confidence
why_it_matters
alternative_explanations
possible_resolution
artifact_id
source_locator
created_at
```

固定枚举：

```text
nature: flaw | scope_limitation | reporting_gap | concern
basis: demonstrated | potential | not_reported
severity: critical | major | moderate | minor
confidence: high | medium | low
```

`nature` 回答“这是什么性质的问题”，`basis` 回答“当前证据状态是什么”，`basis_rationale` 解释为什么属于该状态。已经由 Methods/Results/Supplement 明确建立的设计事实、样本事实、未采集来源或方法固有限制使用 `demonstrated`；尚未直接证实的风险/替代解释才使用 `potential`；只知道论文没有报告的信息使用 `not_reported`。

### `leads`

```text
id
paper_id
type
title
identifier
url
purpose
priority
status
artifact_id
source_locator
```

`type` 可表示 paper、dataset、code、protocol、database、method 等下一跳。

### `relations`

所有明确关系统一保存：

```text
id
subject_type
subject_id
predicate
object_type
object_id
confidence
note
created_at
```

典型 predicate：

```text
USES
PRODUCES
DIRECTLY_SUPPORTS
INDIRECTLY_SUPPORTS
QUALIFIES
CONTRADICTS
DOES_NOT_TEST
LIMITS
CHALLENGES
WEAKENS
SHARES_SAMPLES_WITH
SHARES_DATA_WITH
CITES
```

跨论文或跨知识单元关系通过 `research-db relate` 写入；调用方必须提供明确 `note` 说明核验依据。脚本只校验实体存在性、predicate 与重复关系，不自动推断“共享数据”“支持”“冲突”等科研语义；模糊 `SUPPORTS` 继续拒绝。

共享 cohort / sample / dataset 的 evidence family 第一版通过关系图 connected component 动态计算，不额外维护重复 source of truth。

### `change_log`

SQLite 是二进制文件，Git 无法提供字段级可读 diff；所有脚本写入同时记录语义 change log：

```text
id
timestamp
action
entity_type
entity_id
paper_id
reason
run_id
summary
```

Git 保存数据库版本快照，`change_log` 保存数据库内部语义演化。

## 5. 写入契约：Bundle + Transaction

Skill 默认不让 Agent 对每个 Method / Observation / Issue 分散执行大量 `INSERT`，也不把直接 SQL 当作正常写入接口。

### Paper acquisition bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-paper
```

默认读取 `.research/bundles/paper.json`。只有调试或外部调用需要时才显式传入其他 JSON 路径或 `-`（stdin）；内部 bundle 不放在科研项目根目录。

输入 JSON 至少包含 `title`、稳定论文身份和一个 `kind=main_text` 的真实 artifact。论文身份按 DOI → PMID → 显式 `canonical_identity` 的顺序确定：存在 DOI 时 canonical identity 必须是 `doi:<normalized-doi>`，否则存在 PMID 时为 `pmid:<pmid>`；显式 `canonical_identity` 只用于两者都不存在但调用方已经完成 identity resolution 的情况，`"doi"` 这类 identity type 标签不是论文身份。`artifacts[].path` 相对路径按科研项目根目录解析；文件必须真实存在。

写入前完成 artifact 存在性与论文身份检查；正式写入使用单一事务，自动分配 `P000001` 形式的 Paper ID，并把来源文件复制到 `literature/papers/<paper-id>/` 的 canonical artifact 目录。主文使用 `paper.<ext>`，补充材料按 `kind` 生成稳定文件名；来源 staging 文件没有后缀时根据 `content_type` 推断 canonical 扩展名，无法推断时拒绝写入，不生成无扩展名的 canonical 主文。原来源文件保持不变。数据库登记最终路径、版本、来源 URL 与 `retrieved_at`，缺少获取时间时由 ingest 记录当前时间。DOI 会规范化后去重；发现已存在身份、目标 Paper 目录冲突或任一 artifact 无效时整次数据库写入失败，并清理本次新建的 canonical artifact 目录。

### Reconstruction bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-reading
```

默认读取 `.research/bundles/reconstruction.json`。bundle 是内部事务载荷，不是用户需要维护或阅读的科研文档。

bundle 至少包含 `paper_id`、`artifacts_checked`、`sections_checked`、`extraction_checks`，以及至少一种知识单元：

```text
methods[]
experiments[]
observations[]
claims[]
leads[]
relations[]
```

每个新知识单元提供当前 bundle 内唯一的 `ref`。relation 使用 `subject_type + subject_ref/id` 与 `object_type + object_ref/id`，脚本在事务内把临时 ref 解析为数据库主键；Observation 也可通过 `experiment_ref` 连接当前 bundle 的 Experiment。每个 Method / Experiment / Observation / Claim / Lead 都必须定位到具体 artifact，并保存能够回到原文的 subsection / page / figure/table / supplement item 等 `source_locator`；仅写 `Methods`、`Results`、`Discussion`、`Abstract` 等顶层 section 会被 ingest/validate 直接拒绝。

所有论文重建（Reconstruction）都必须在 `extraction_checks` 中确认 `observation_semantics_checked=true`。深度抽取（deep_extraction）额外要求图表、定量结果、补充材料和代码/数据均形成显式检查状态。补充材料使用 `supplement_presence = present | none_found | unclear`，代码/数据对称使用 `code_data_presence = present | none_found | unclear`；对应状态为 `checked | not_applicable | access_limited`。只有存在性确认为 `none_found` 时才允许 `not_applicable`。正文或机器可读取论文页面如果明确暴露数据可用性声明以及具体下载/仓储位置，validator 会拒绝 `code_data_presence=none_found`。代码/数据标记 `checked` 必须引用至少一个成功的 `code_data` 获取尝试；标记 `access_limited` 必须引用真实失败尝试并完成替代路径审计。数据库一旦已登记补充材料，`artifacts_checked` 仍必须覆盖全部已取得附件。存在相关定量结果时至少一个观察结果（Observation）保存非空统计信息；若确实没有相关定量结果，则必须明确说明原因。

证据关系不能把“方向一致”一律写成 `SUPPORTS`。科研层优先使用 `DIRECTLY_SUPPORTS | INDIRECTLY_SUPPORTS | QUALIFIES | CONTRADICTS | DOES_NOT_TEST`；其中 `INDIRECTLY_SUPPORTS`、`QUALIFIES`、`DOES_NOT_TEST` 必须通过 relation `note` 说明 inference gap 或边界。脚本只校验结构，主模型负责判断证据是否真的达到目标 Claim 的 descriptive / association / causal / mechanistic 层级。

脚本顺序：validate bundle → `BEGIN IMMEDIATE` → 建立 Reconstruction reading run → 写入知识单元 → 解析并校验 relations → write change log → 将论文更新为 `reading_status=reconstructed` → `COMMIT`。任何结构、source artifact 或 relation 校验失败都 `ROLLBACK`，不能留下半篇论文。已完成 Reconstruction 的 Paper 默认拒绝重复导入，避免无意复制知识单元。

### Critical Audit bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-critical
```

默认读取 `.research/bundles/critical.json`；同样属于隐藏的内部事务载荷。

Critical Audit 必须建立在已经完成的 Reconstruction 上，并且不能把 `FULL_SCAN` Reconstruction 直接升级成 `DEEP_EXTRACTION`。bundle 至少包含：

```text
paper_id
artifacts_checked
sections_checked
issues[]
relations[]
sidecar_path          -- 可选
```

每个 Issue 使用 bundle `ref`，并保存 category、nature、assessment、basis、`basis_rationale`、severity、confidence、具体 artifact 与精确 source locator。`basis_rationale` 是强制字段：必须说明为什么该 Issue 属于 `demonstrated`、`potential` 或 `not_reported`，不能只重复 assessment。Issue 可通过 `target_type + target_id` 指向 Reconstruction 已写入的 Claim / Observation / Method / Experiment；`ingest-reading` 返回的 `refs` map 可用于取得这些内部 ID。Issue 与 Claim/Observation 的 `LIMITS`、`CHALLENGES`、`WEAKENS`、`QUALIFIES` 等明确关系继续写入 `relations`。

若 Agent 已在论文 canonical 目录写好人类必读 `README.md`，可通过 `sidecar_path` 一并关联；脚本只链接已存在文件，不负责机械生成 synthesis。全部校验通过后才将论文更新为 `reading_status=extracted`、`critical_status=critically_reviewed`。任何 target、artifact、relation 或 sidecar 错误都整次回滚。

## 6. CLI

当前可用：

```bash
uv run scripts/research_db.py init
uv run scripts/research_db.py migrate
uv run scripts/research_db.py record-search
uv run scripts/research_db.py record-access-attempt
uv run scripts/research_db.py access-attempts
uv run scripts/research_db.py search-runs
uv run scripts/research_db.py candidates
uv run scripts/research_db.py update-candidate <candidate-id>
uv run scripts/research_db.py merge-candidates <keep-id> <merge-id> --reason "..."
uv run scripts/research_db.py discovery-status
uv run scripts/research_db.py ingest-paper
uv run scripts/research_db.py ingest-reading
uv run scripts/research_db.py ingest-critical
uv run scripts/research_db.py relate
uv run scripts/research_db.py evidence <query>
uv run scripts/research_db.py status
uv run scripts/research_db.py validate
uv run scripts/research_db.py validate --completion
```

默认从当前目录向上定位 `RESEARCH.md` 或 `.research/research.sqlite`；也可用全局 `--project <path>` 显式指定科研项目根目录。`init` 同时创建 `.research/bundles/`；`record-search` 默认读取 `search.json`，`record-access-attempt` 默认读取 `access-attempt.json`，`update-candidate` 默认读取 `candidate-update.json`，三个 ingest 命令分别读取 `paper.json`、`reconstruction.json`、`critical.json`；都可显式传其他 JSON 路径或 `-` 从 stdin 读取。命令输出结构化 JSON。

知识读取接口当前可用：

```text
research-db paper P000001
research-db search <query>
research-db methods [query]
research-db issues [query] [filters]
research-db claims [query]
research-db evidence <query>
research-db related P000001
research-db history P000001
research-db record-dataset [bundle]
research-db datasets
research-db record-analysis [bundle]
research-db analyses
research-db record-hypothesis-set [bundle]
research-db hypothesis-sets
research-db record-design [bundle]
research-db designs
research-db record-hypothesis-evaluation [bundle]
research-db hypothesis-evaluations
research-db record-communication [bundle]
research-db communications
research-db status
research-db validate
```

Skill 与其他 Agent 通过 CLI / structured JSON 读取数据库，避免 Prompt 与 SQL schema 过度耦合。低层 SQL 可以供脚本实现与调试使用，但不是正常 Agent 工作流。

## 7. 检索

检索层使用 SQLite 普通索引 + FTS5，不引入向量数据库。索引至少覆盖：

```text
paper title
method name / description / reusable_notes
experiment question
observation statement
claim statement
issue assessment / alternative_explanations
lead title
```

Agent 根据用户问题生成关键词、同义词或结构过滤条件；SQLite 返回候选 knowledge units，Agent 再读取候选和必要原文完成解释。`paper` 返回 identity/artifact/reading-run/counts，`methods`/`claims`/`issues` 支持 Paper 与文本/问题过滤，`history` 返回语义 change log，`related` 根据跨 Paper relation 动态聚合关联论文。数据库负责记忆与定位，原始论文负责最终核验。

`research-db evidence <query>` 先检索相关 Claim / Observation / Issue，再做有界关系展开，补回相邻 Observation / Claim / Issue 与来源 Paper；随后沿 `SHARES_DATA_WITH` / `SHARES_SAMPLES_WITH` 计算与命中论文相连的 evidence family。packet 同时返回 `seed_units`、展开后的 `evidence_units`、`relations`、`papers` 与 `evidence_families`。共享数据家族用于避免把同一 cohort/sample/dataset 的多篇论文当成独立 replication；脚本负责检索图，不负责用硬编码评分替代科研判断。

## 8. Sidecar

计划接口可以提供：

```bash
research-db paper-context P000001 --for-sidecar
```

它返回 identity、high-value methods、major observations、main claims、critical/major issues、reusable knowledge 与 innovation candidates。Agent据此结合全文理解更新论文旁边的 `README.md`；sidecar 目标是短小的人类 synthesis，而不是模板化 dump。

## 9. Validate

`research-db validate` 相当于科研知识库的 integrity check。至少检查：

- duplicate DOI / PMID / canonical identity，以及 DOI/PMID 与 canonical identity 不一致；
- Candidate 的 identity/relevance/acquisition 状态自洽：`excluded` 有 exclusion reason，`acquired` 已关联 Paper，已关联 Paper 的 DOI/PMID 与 Candidate 不冲突，同一稳定 DOI/PMID 不存在多个 Candidate；`unavailable` 必须有足够的 Acquisition Attempt provenance、publisher/open-resolution 路径覆盖，且不能只记录一个失败 publisher PDF，也不能与仍为 active 的 `acquired` attempt 并存；superseded attempt 必须有有效 replacement 与 supersession reason；
- canonical `main_text` artifact 缺少文件扩展名；
- dangling relation / nonexistent target；
- observation 指向不存在的 experiment；
- issue target 不存在；
- artifact path 缺失；
- reconstructed 状态缺少已完成 reconstruction run，或 Reconstruction 缺少 Observation 语义自审；
- `deep_extraction` 缺少 figures/tables、quantitative results、supplement、code/data 检查状态；Supplement presence/status 自相矛盾；`not_applicable/access_limited` 没有理由；`access_limited` 缺少可核验 Acquisition Attempt；已取得 supplement 未全部进入 `artifacts_checked`；或声明存在定量结果却未保存 `statistics_json`；
- Critical Audit 将 `full_scan` Reconstruction 越级标成 `deep_extraction`；
- critically reviewed 状态缺少已完成 critical audit run；
- Issue 缺少 `basis_rationale`，或 `not_reported` issue 缺少足够 artifact / source inspection 记录；
- Method / Experiment / Observation / Claim / Issue / Lead 的 `source_locator` 只有 `Methods`、`Results`、`Discussion` 等模糊顶层 section；
- Dataset provenance path、本地 Dataset artifact、Analysis 入口/代码/结果 artifact 缺失；
- Project Observation 指向其他 Analysis 的结果 artifact；
- confirmatory Analysis 已进入 frozen/completed 却没有记录 freeze commit；Analysis 已结构化关联 Design 时，Design 不存在或 estimand 与 Design 不一致；
- Hypothesis Set / Research Design 的 canonical artifact 缺失、冻结状态缺少 freeze commit、Design 引用不存在的 Hypothesis Set、未解决 feasibility 没有说明，或 execution-ready 与 feasibility 状态矛盾；
- Hypothesis Evaluation 引用未完成 Analysis、引用的解释 artifact 不属于同一 Analysis，或其 Hypothesis Set 与 Analysis 所实现 Design 不一致；
- Communication artifact 指向不存在文件或不存在的 Communication Product；
- schema version / migration 状态异常；
- sidecar pointer 指向不存在文件时给出明确错误或 warning。

对“critically reviewed 但没有 Issue”这类可能合法的情况给 warning，而不是为了满足 schema 强迫 Agent 编造批判。

普通 `validate` 的 structured result 还返回 `schema_compatible`。它只描述当前数据库结构是否可由本版本 Skill 安全解释：`PRAGMA user_version` 必须等于当前 schema、`meta.schema_version` 必须与其一致，且当前必需表完整。它不等同于 `ok`；例如数据库内容存在 integrity error 时，可以出现 `schema_compatible=true` 但 `ok=false`。数据库不存在时 `schema_compatible=false`。

`validate --completion` 在 `schema_compatible=false` 时不得继续执行依赖当前 schema 的 Discovery / Literature / Planning / Downstream / Communication readiness。它必须直接返回 `completion=false`、`completion_checked=true`，把这些 readiness 标记为 `checked=false` 并说明 `schema_incompatible`（数据库不存在时为 `database_missing`），同时保留普通 `validate` 的版本/缺表错误。对历史项目这是一项**工具兼容性门禁**，不是科学失败判定；在用户未授权维护时不得自动迁移。先运行 `research-db status` 核对 `migration_needed`，获得维护授权后再执行 `research-db migrate` 并重新运行 completion gate。

历史 schema 的只读查询应尽量返回该版本真实可表达的 provenance，而不是访问后续 migration 才新增的列或表并泄漏低层异常。当前 `research-db analyses` 会在旧 schema 上返回已有 Analysis / Dataset / artifact / Observation，并通过 `schema_capabilities` 明确标记 `analysis_design_link` 与 `dataset_artifact_timing` 是否由该数据库版本建模；能力为 `false` 时，相应派生字段为 `null`，表示“该 schema 不具备此 provenance 维度”，不能解释成已经核验为空。

`research-db discovery-status` 是文献发现（Literature Discovery）的闭合门禁：存在 `relevance_status=pending`、未闭合的 `core + relevant` 或 `high + relevant` Candidate、仍处于 `user_access_status=required` 的用户协同任务，或重复稳定身份时返回 `ready_for_saturation=false`。高优先级 Candidate 的 `defer_reason` 不再构成闭合依据。主题型文献发现若已有至少 2 个相关 Candidate，还必须保留检索策略来源、至少一次后向/前向引用追踪，并覆盖至少两个发现策略家族；否则即使 Candidate 队列表面清空也不能宣称实践性概念饱和（practical conceptual saturation）。

`research-db validate --completion` 是“本轮有边界科研工作流已完成”的最终门禁。它先执行普通数据库校验，再检查文献发现闭合与文献语义完成状态：所有相关且已获取全文的候选论文必须有可审计正文获取记录与合格获取依据，并完成论文重建（Reconstruction）和批判性审阅（Critical Audit）；所有核心且已获取论文必须有真实深度抽取（DEEP_EXTRACTION）重建；主题型文献发现已有至少两篇完成审阅的论文时，必须存在至少一条连接不同论文的科学关系，共享样本/共享数据/引用关系不计作该门禁。对于为当前问题**定向直接入库**、没有经过 Candidate/Discovery 队列的 `active/acquired` Paper，仍必须留下合格的正文获取 provenance 并完成 Reconstruction + Critical Audit；“本轮不是 Literature Discovery”不能成为绕过关键论文阅读闭合的路径。

项目存在 `data/` 或 `analysis/` 科研资产时，完成验证还检查下游 provenance：被 Git 跟踪的数据/分析文件不能游离在数据库之外；已完成 Analysis 必须关联 Dataset、至少一个 estimate artifact 和至少一个项目 Observation；确认性 Analysis 的 freeze commit 必须存在且是当前 HEAD 的祖先，主要计划/代码/输入和默认 Dataset freeze scope 在 freeze 时已经存在，且这些路径在后续提交历史中从未被改写，而本轮结果 artifact 在该 freeze 时尚未出现。结果后新增但不属于该执行快照的 canonical Dataset provenance 通过 `analysis_dataset_artifact_timing.timing_role=post_result_context` 绑定到具体 Analysis；除必须在 freeze 时不存在外，其首次 Git 提交还必须已经包含当前 Analysis 的至少一个 result artifact，才有机械证据支持“post-result”时序，不再需要错误登记为 Analysis `result`。若确认性 Analysis 与已登记 Research Design 的 estimand/uncertainty 对齐，则必须通过 `design_slug` 显式连接；关联 Design 必须先冻结，且其 freeze 不能晚于 Analysis freeze。只有所有完成门禁均通过时才返回 `completion=true`；失败时返回 `completion=false`。`completion_checked=true` 只表示本次确实执行了完成门禁，不能与通过状态混淆。这样 `completion=true` 才能说明预先冻结与结果 provenance 真实存在，而不是事后写在 README 里。

项目存在 `hypotheses/` 或 `designs/` canonical artifact 时同样不能游离在数据库之外。冻结的 Hypothesis Set / Design 必须登记有效 Git freeze commit；该提交必须是当前 HEAD 的祖先并真实包含相应 artifact，Design 的 freeze 还必须同时包含其关联 Hypothesis Set，且不能早于 Hypothesis Set 的冻结。`feasibility_status=unresolved` 可以完成“科研设计工作流”，但只表示设计已形成并明确 blocker，不能被解释成实验已经 execution-ready。一个 linked confirmatory Analysis 完成后，如果它已经被用于更新关联 Hypothesis Set，completion 还要求存在对应 Hypothesis Evaluation，并由 Evaluation 指回当前 Analysis 已登记的解释/结果 artifact；`hypothesis_sets.status=frozen` 本身绝不作为结果后科研判定的替代。

项目存在 `communication/` 传播产物时，完成验证还要求这些文件登记到 Communication Product，并记录其 pre-communication `source_commit`。已登记传播 artifact 会进入 Git 完整性检查；`derived_output` 不能在 source commit 中已经存在，`source_support` 必须在 source commit 中已经存在。若 source commit 之后 Hypothesis / Design / Data / Analysis 等已登记科学 artifact 又发生变化，旧传播稿必须基于新的稳定 evidence commit 重新审阅。这个 Git path 集合只承担完整性门禁，不把 Communication artifact 提升为 canonical scientific source。

对于以中文为主体的科研项目，完成验证还会检查 `RESEARCH.md`、论文侧记、Hypothesis / Design、Dataset provenance、Analysis 人类入口以及已登记 Communication 文本中的明显大段英文科研叙述，并在这些人类可读科研文本中识别一小组已有成熟中文表述却裸用的常见英文术语。代码块、内联代码、路径、URL 和首次中英文括注不参与该术语检查。完成门禁同时返回 `project_state` readiness：`RESEARCH.md` 必须保留 `Objective`、`Current Loop`、`Active Uncertainty`、`Current State`、`Active Work`、`Open Threads`、`Key Decisions`、`References` 八个二级 section，`Current Loop` 必须是规定定位词，且 `Active Work` 不能仍把 Git commit、`validate --completion`、clean-tree 等已经结束的收尾动作写成当前工作。这个机械检查只用于防止 current-state map 陈旧，不对科学问题是否解决作自动判断。随后要求项目根目录本身是独立版本仓库（Git repository）顶层、已经存在至少一个提交，且全部声明为需要 Git 跟踪的科研/传播 artifact 已被版本管理跟踪且没有未提交修改。普通 `validate` 通过不能替代这个完成门禁；`completion=true` 只表示该有边界完成门禁通过，仍不能解释成科学问题本身已经解决。
