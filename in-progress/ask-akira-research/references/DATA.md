# Research Data Contract

Data 阶段的任务是把真实 observation source 以可追溯、可重建且不混淆 raw / derived 的方式带入科研项目。数据存在不等于 evidence 已产生；只有与 Design / Hypothesis 的 target contrast 对齐并经过 Analysis 后，数据才进入解释层。

## 1. 进入条件

进入 `DATA` 前应知道数据为什么被需要：

- 来自 [`DESIGN.md`](DESIGN.md) 的新采样 / measurement / experiment；或
- 已存在的数据集被识别为可以直接降低当前 Active Uncertainty。

如果数据访问、伦理审批、样本、设备、凭据或外部机构授权尚未满足，记录为明确 blocker 并停在这里；不得用虚构数据、假设样本量或模型生成值替代真实数据继续 Analysis。

## 2. Raw / curated / derived 分层

数据至少区分：

- **raw**：原始仪器输出、原始测序、原始问卷/采集记录、原始下载数据等；进入项目后保持只读语义，不原地修改；
- **curated**：对 raw 做明确、可追溯的纠错、样本映射、单位标准化、metadata 整理或人工 adjudication 后的版本；
- **derived**：由脚本或分析流程从 raw/curated 计算出的矩阵、特征、统计中间结果、图表输入等。

任何会改变值或样本含义的“清洗”都不能静默覆盖 raw。修正产生新 artifact，并记录来源与变换。

## 3. 数据集 identity 与 provenance

经过真实纵向数据黑盒验证后，稳定的数据集身份与 provenance 已进入 `research.sqlite`：使用 `research-db record-dataset` 登记 Dataset，并把 `data/<dataset-slug>/README.md` 作为人类可读 provenance 入口。原始/整理数据本身仍是独立 artifact，不把文件内容塞进 SQLite；大型或受控数据允许保留在外部存储，只记录位置、版本和为什么不要求 Git 跟踪。

至少记录：

```text
Dataset identity / accession / local name
Purpose in current research
Source / provider
Source URL or external location (if applicable)
Version / release / acquisition batch
Retrieved / received / collected at
Population / experimental system
Sample / subject identifiers and mapping rules
Raw artifact locations
Access / ethics / consent constraints
Known missingness / exclusions / anomalies
Processing entrypoint or pointer
```

有 DOI、accession、repository ID、instrument run ID、sample ID 等稳定身份时优先使用它们。日常科研不默认对所有 artifact 计算 SHA；只有来源缺少稳定版本、跨介质传输完整性需要验证、或上游已经提供 checksum 时才记录 checksum。对能够由明确软件版本/官方对象稳定重导出的公开数据，不要为了“显得严谨”额外计算 checksum；身份、版本、来源和可重复导出路径已经足以承担常规 provenance。

## 4. Sample identity 与 unit of inference

每个进入 Analysis 的 row / column / file 必须能回答它对应的 biological / participant / experimental unit 是什么。

需要明确区分：

- participant / animal / biological specimen；
- aliquot / extraction / library / lane / technical replicate；
- longitudinal timepoint；
- experimental batch / plate / sequencing run；
- pooled sample。

Technical replicate 不得静默当成独立 biological `n`。样本重命名、合并、排除或一对多映射必须有可追踪规则。

## 5. Metadata 与 missingness

对当前 Design / Analysis 可能影响解释的 metadata 应尽早保留，包括 exposure、group、time、covariate、batch、processing、collection/storage、QC 与缺失原因。

Missingness 不只记录空值，还要尽可能区分：

- not collected；
- collected but failed；
- below detection；
- excluded by pre-defined QC；
- unavailable / lost；
- unknown。

无法区分时保留 unknown，不用模型猜测缺失原因。

## 6. 数据变换可重建

从 raw/curated 到 derived 的每一步应由代码、命令、workflow 或明确人工记录重建。正常路径不依赖手工在 GUI 中改完后只保存最终文件。

每个重要 derived artifact 至少能回到：

```text
input artifact(s)
processing code / command / workflow
parameters / reference / database version
software / environment version where material
output artifact
```

随机过程记录 seed 或能够重建随机状态；外部 reference database / genome / annotation 的版本必须在会影响结果时固定。若 curated / analysis-ready 数据由项目内脚本或 workflow 生成，该处理入口本身属于 Dataset provenance：使用 `record-dataset` 在核心 Dataset 身份不变的前提下追加 `role=other` 的 artifact，使脚本即使位于 `scripts/` 而非 `data/` 下也进入 canonical Git gate。Dataset 核心身份已经登记后不得借追加 artifact 静默改写；身份/版本变化应建立新 Dataset。

## 7. QC 不等于删数据

QC 先产生诊断，再按 Design 中预先定义或科学上可辩护的规则决定 exclusion / correction。结果可见后新增的 exclusion rule 必须标成 post hoc，并进入 sensitivity analysis，而不是覆盖原规则。

QC 至少考虑当前 assay 的关键失败模式；例如 sequencing 的 read quality / contamination / depth / mapping，仪器的 calibration / drift，问卷的 impossible values / duplicate records。不存在统一 QC checklist 能替代 assay-specific 判断。

## 8. 数据冻结与可分析版本

用于 primary / confirmatory Analysis 的输入应有明确 data freeze，例如 Git-tracked manifest、版本目录、repository release 或其他稳定 snapshot。冻结后：

- raw 不覆盖；
- curated 修正形成新版本；
- primary analysis 使用哪个 freeze 必须明确；
- freeze 后发现的数据问题记录 amendment，并判断是否影响 confirmatory status。

大型或受控数据是否进入 Git、外部存储或远程仓库由项目实际约束决定；Skill 不默认要求把所有 raw binary 纳入 Git。对本地且声明 `git_tracking=required` 的 Dataset artifact，`validate --completion` 会把它纳入 canonical Git provenance；声明 `not_required` 时必须给出具体理由。`git_tracking` 只回答“这个 artifact 是否属于需要版本控制的 canonical provenance”，不能同时承担“它是否属于某次确认性 Analysis 的结果前冻结”这一关系语义。默认情况下，Analysis 所连接 Dataset 的全部 local + `git_tracking=required` artifact 都属于该 Analysis 的 freeze scope。若来源核验、测量语义说明或其他 provenance/context artifact **确实是在该 Analysis 的结果可见后才新增，且没有参与该次输入/执行**，在 `record-analysis` 中用 `dataset_artifact_timing` 把该 Analysis 与该 artifact 标为 `timing_role=post_result_context` 并说明 `reason`；文件仍保持 canonical Git provenance。完成门禁要求这类 artifact 在 freeze 中不存在，并且它首次进入 Git 历史时已经能看到当前 Analysis 的至少一个已登记 result artifact；只晚于 freeze、却早于结果提交的文件不能事后改标为 `post_result_context`。该关系只对当前 Analysis 生效：后续 Analysis 若未再次声明，仍把该 artifact 作为正常 pre-result context 纳入新的 freeze。结果后补充 provenance 时新增独立 artifact，不覆盖已经进入 freeze 的 Dataset provenance、raw、curated 或其他输入版本。

## 9. 安全与受控数据

受控人类数据、个人信息、临床数据或其他敏感数据遵守其 consent、DUA、伦理审批和存储边界。科研数据库只保存完成任务所需的最少 metadata / pointer；不要为了方便检索把受限 raw data、身份信息或凭据复制进不合适的 artifact。

## 10. 完成条件

按 [`ANALYSIS.md`](ANALYSIS.md) 进入 `ANALYSIS` 前至少满足：

1. 当前分析输入的数据身份、来源和版本可确认；
2. raw / curated / derived 边界清楚，raw 未被静默覆盖；
3. sample mapping 与 unit of inference 可解释；
4. 关键 metadata、missingness 与 exclusion provenance 已记录；
5. primary analysis 所需 input freeze 已明确；
6. 从 input 到 analysis-ready artifact 的变换可以重建；
7. access / ethics / privacy 条件允许当前分析实际执行。

若任何必需原始数据或访问授权仍由用户/机构掌握且当前不可获得，就在这里形成 blocker；这是需要人类介入的真实边界，而不是让 Agent用近似数据继续。
