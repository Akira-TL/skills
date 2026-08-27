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
reading_runs
methods
experiments
observations
claims
issues
leads
relations
change_log
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
defer_reason            -- high-priority relevant Candidate 未立即获取时的明确延期理由
paper_id
created_at
updated_at
```

同一 Candidate 可以由多次 Search Run 独立发现；`search_run_candidates` 保存 `search_run_id + candidate_id + result_rank + source_result_id/source_url`，避免把重复发现误当独立论文。DOI/PMID 已解析时优先按稳定身份复用 Candidate；没有稳定身份时对规范化后的 title/year 做保守 identity enrichment，以吸收标点、大小写和连字符差异。发现历史上已经存在的重复 Candidate 时使用 `research-db merge-candidates`，把 Search Run provenance 合并到一条 canonical Candidate；不要用 `relevance_status=excluded` 代替 identity reconciliation。论文经 `ingest-paper` 获取后，匹配 Candidate 自动回链 `paper_id` 并更新为 `acquired`。

Candidate ID 主要供数据库内部使用。

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

Observation 只记录数据直接显示的内容，不混入 Method 操作、作者限制、Agent 批判或证据解释。`ingest-reading` 要求 `extraction_checks.observation_semantics_checked=true`；`deep_extraction` 还要求显式完成 figures/tables、quantitative results、supplement 与 code/data 检查。若 `quantitative_results_present=true`，至少一个 Observation 必须保存非空 `statistics_json`；真正影响核心 evidence chain 的作者报告定量结果不能只存在于 derived report。

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

所有 Reconstruction 都必须在 `extraction_checks` 中确认 `observation_semantics_checked=true`。`depth=deep_extraction` 额外要求 `figures_tables_checked=true`、`quantitative_results_checked=true`、`supplement_status` 与 `code_data_status`（`checked | not_applicable | access_limited`），并明确 `quantitative_results_present`。`not_applicable`/`access_limited` 必须分别给出 `supplement_reason`/`code_data_reason`；数据库一旦已登记 supplement artifact，`supplement_status` 不得再为 `not_applicable`；若声明已 `checked`，`artifacts_checked` 必须覆盖全部已登记 supplement artifacts。存在相关定量结果时至少一个 Observation 保存非空 `statistics`；若声明不存在，则必须写 `quantitative_results_reason`。这些检查状态写入 `reading_runs.extraction_checks_json`，使 `validate` 能识别只标了 deep_extraction、实际没有完成定量/附件审计的记录。

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

默认从当前目录向上定位 `RESEARCH.md` 或 `.research/research.sqlite`；也可用全局 `--project <path>` 显式指定科研项目根目录。`init` 同时创建 `.research/bundles/`；`record-search` 默认读取 `search.json`，`update-candidate` 默认读取 `candidate-update.json`，三个 ingest 命令分别读取 `paper.json`、`reconstruction.json`、`critical.json`；都可显式传其他 JSON 路径或 `-` 从 stdin 读取。命令输出结构化 JSON。

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
- Candidate 的 identity/relevance/acquisition 状态自洽：`excluded` 有 exclusion reason，`acquired` 已关联 Paper，已关联 Paper 的 DOI/PMID 与 Candidate 不冲突，同一稳定 DOI/PMID 不存在多个 Candidate；
- canonical `main_text` artifact 缺少文件扩展名；
- dangling relation / nonexistent target；
- observation 指向不存在的 experiment；
- issue target 不存在；
- artifact path 缺失；
- reconstructed 状态缺少已完成 reconstruction run，或 Reconstruction 缺少 Observation 语义自审；
- `deep_extraction` 缺少 figures/tables、quantitative results、supplement、code/data 检查状态；`not_applicable/access_limited` 没有理由；声明 supplement 已检查却未在 `artifacts_checked` 中留下附件证据；或声明存在定量结果却未保存 `statistics_json`；
- Critical Audit 将 `full_scan` Reconstruction 越级标成 `deep_extraction`；
- critically reviewed 状态缺少已完成 critical audit run；
- Issue 缺少 `basis_rationale`，或 `not_reported` issue 缺少足够 artifact / source inspection 记录；
- Method / Experiment / Observation / Claim / Issue / Lead 的 `source_locator` 只有 `Methods`、`Results`、`Discussion` 等模糊顶层 section；
- schema version / migration 状态异常；
- sidecar pointer 指向不存在文件时给出明确错误或 warning。

对“critically reviewed 但没有 Issue”这类可能合法的情况给 warning，而不是为了满足 schema 强迫 Agent 编造批判。

`research-db discovery-status` 是 Literature Discovery 的 closure gate：存在 `relevance_status=pending`、未闭合的 `core + relevant` Candidate、没有 `defer_reason` 的 `high + relevant + queued/pending` Candidate 或重复稳定身份时返回 `ready_for_saturation=false`。主题型 Discovery 若已有至少 2 个 relevant Candidate，且轨迹包含 query search 或 related-work 扩展，还必须有显式 `discovery_method` provenance、至少一次 `backward_citation`/`forward_citation`，并覆盖至少两个 discovery family；否则即使 Candidate 队列已清空也不能宣称 practical conceptual saturation。纯 `exact_work` 定向阅读不被误判为 saturation workflow。

`research-db validate --completion` 是“本轮科研项目已完成”的最终门禁。它先执行普通数据库校验，再检查 Discovery closure，并要求项目根目录本身是 Git repository top-level、已经存在至少一个 commit、`RESEARCH.md`、`.research/research.sqlite`、canonical paper artifacts 与 sidecar 已被 Git 跟踪且没有未提交修改。普通 `validate` 通过不能替代这个 completion gate。
