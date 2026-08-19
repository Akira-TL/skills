# Research SQLite Contract

本文件定义 `ask-akira-research` 的项目级科研知识数据库契约。当前已实现 schema migration，以及 `init`、`migrate`、`ingest-paper`、`status`、`validate`；Reconstruction / Critical Audit bundle、FTS 检索与 evidence 查询仍按本契约继续实现。

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

## 3. 核心表

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
identity_status
relevance_status
relevance_reason
paper_id
created_at
updated_at
```

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
effect
statistics_json
scope
certainty
artifact_id
source_locator
```

Observation 只记录数据直接显示的内容，不混入作者解释。

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

`nature` 回答“这是什么性质的问题”，`basis` 回答“我们凭什么这样判断”。例如只覆盖年轻男性而限制外推范围可记为 `scope_limitation + demonstrated`，不把明确的研究边界误称为 flaw。

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
SUPPORTS
CONTRADICTS
CHALLENGES
WEAKENS
SHARES_SAMPLES_WITH
SHARES_DATA_WITH
CITES
```

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

## 4. 写入契约：Bundle + Transaction

Skill 默认不让 Agent 对每个 Method / Observation / Issue 分散执行大量 `INSERT`，也不把直接 SQL 当作正常写入接口。

### Paper acquisition bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-paper paper.json
```

输入 JSON 至少包含 `title`、稳定论文身份和一个 `kind=main_text` 的真实 artifact。稳定身份来自 DOI、PMID 或调用方已经完成 identity resolution 后提供的 `canonical_identity`。`artifacts[].path` 相对路径按科研项目根目录解析；文件必须真实存在。

写入前完成 artifact 存在性与论文身份检查；正式写入使用单一事务，自动分配 `P000001` 形式的 Paper ID，并把来源文件复制到 `literature/papers/<paper-id>/` 的 canonical artifact 目录。主文使用 `paper.<ext>`，补充材料按 `kind` 生成稳定文件名；原来源文件保持不变。数据库登记最终路径、版本、来源 URL 与 `retrieved_at`，缺少获取时间时由 ingest 记录当前时间。DOI 会规范化后去重；发现已存在身份、目标 Paper 目录冲突或任一 artifact 无效时整次数据库写入失败，并清理本次新建的 canonical artifact 目录。

### Reconstruction bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-reading reconstruction.json
```

bundle 至少包含 `paper_id`、`artifacts_checked`、`sections_checked`，以及至少一种知识单元：

```text
methods[]
experiments[]
observations[]
claims[]
leads[]
relations[]
```

每个新知识单元提供当前 bundle 内唯一的 `ref`。relation 使用 `subject_type + subject_ref/id` 与 `object_type + object_ref/id`，脚本在事务内把临时 ref 解析为数据库主键；Observation 也可通过 `experiment_ref` 连接当前 bundle 的 Experiment。来源定位可使用 `artifact_id`、唯一 `artifact_kind` 或 canonical `artifact_path`，并保存 section / page / figure/table 等 `source_locator`。

脚本顺序：validate bundle → `BEGIN IMMEDIATE` → 建立 Reconstruction reading run → 写入知识单元 → 解析并校验 relations → write change log → 将论文更新为 `reading_status=reconstructed` → `COMMIT`。任何结构、source artifact 或 relation 校验失败都 `ROLLBACK`，不能留下半篇论文。已完成 Reconstruction 的 Paper 默认拒绝重复导入，避免无意复制知识单元。

### Critical Audit bundle

当前接口：

```bash
uv run scripts/research_db.py ingest-critical critical.json
```

Critical Audit 必须建立在已经完成的 Reconstruction 上。bundle 至少包含：

```text
paper_id
artifacts_checked
sections_checked
issues[]
relations[]
sidecar_path          -- 可选
```

每个 Issue 使用 bundle `ref`，并保存 category、nature、assessment、basis、severity、confidence 与 source locator。Issue 可通过 `target_type + target_id` 指向 Reconstruction 已写入的 Claim / Observation / Method / Experiment；`ingest-reading` 返回的 `refs` map 可用于取得这些内部 ID。Issue 与 Claim/Observation 的 `LIMITS`、`CHALLENGES`、`WEAKENS`、`QUALIFIES` 等明确关系继续写入 `relations`。

若 Agent 已在论文 canonical 目录写好人类必读 `README.md`，可通过 `sidecar_path` 一并关联；脚本只链接已存在文件，不负责机械生成 synthesis。全部校验通过后才将论文更新为 `reading_status=extracted`、`critical_status=critically_reviewed`。任何 target、artifact、relation 或 sidecar 错误都整次回滚。

## 5. CLI

当前可用：

```bash
uv run scripts/research_db.py init
uv run scripts/research_db.py migrate
uv run scripts/research_db.py ingest-paper paper.json
uv run scripts/research_db.py ingest-reading reconstruction.json
uv run scripts/research_db.py ingest-critical critical.json
uv run scripts/research_db.py status
uv run scripts/research_db.py validate
```

默认从当前目录向上定位 `RESEARCH.md` 或 `.research/research.sqlite`；也可用全局 `--project <path>` 显式指定科研项目根目录。命令输出结构化 JSON。

后续接口目标：

```text
research-db paper P000001
research-db search <query>
research-db methods <query>
research-db issues [filters]
research-db claims <query>
research-db evidence <query>
research-db related P000001
research-db history P000001
research-db status
research-db validate
```

Skill 与其他 Agent 通过 CLI / structured JSON 读取数据库，避免 Prompt 与 SQL schema 过度耦合。低层 SQL 可以供脚本实现与调试使用，但不是正常 Agent 工作流。

## 6. 检索

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

Agent 根据用户问题生成关键词、同义词或结构过滤条件；SQLite 返回候选 knowledge units，Agent 再读取候选和必要原文完成解释。数据库负责记忆与定位，原始论文负责最终核验。

`research-db evidence <query>` 先检索相关 Claim / Observation / Issue，再沿 `relations` 展开支持、冲突、批判、共享数据与来源 Paper，输出 machine-readable evidence packet。脚本负责检索图，不负责用硬编码评分替代科研判断。

## 7. Sidecar

计划接口可以提供：

```bash
research-db paper-context P000001 --for-sidecar
```

它返回 identity、high-value methods、major observations、main claims、critical/major issues、reusable knowledge 与 innovation candidates。Agent据此结合全文理解更新论文旁边的 `README.md`；sidecar 目标是短小的人类 synthesis，而不是模板化 dump。

## 8. Validate

`research-db validate` 相当于科研知识库的 integrity check。至少检查：

- duplicate DOI / PMID / canonical identity；
- dangling relation / nonexistent target；
- observation 指向不存在的 experiment；
- issue target 不存在；
- artifact path 缺失；
- reconstructed 状态缺少已完成 reconstruction run；
- critically reviewed 状态缺少已完成 critical audit run；
- `not_reported` issue 缺少足够 artifact / source inspection 记录；
- schema version / migration 状态异常；
- sidecar pointer 指向不存在文件时给出明确错误或 warning。

对“critically reviewed 但没有 Issue”这类可能合法的情况给 warning，而不是为了满足 schema 强迫 Agent 编造批判。
