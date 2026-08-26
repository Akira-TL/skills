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

当前 Data 模型尚未固化进 `research.sqlite` schema；在真实项目验证前，按需使用 `data/<dataset-slug>/README.md` 保存该数据集的人类可读 provenance，文件本身或外部存储保持独立 artifact。

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

有 DOI、accession、repository ID、instrument run ID、sample ID 等稳定身份时优先使用它们。日常科研不默认对所有 artifact 计算 SHA；只有来源缺少稳定版本、跨介质传输完整性需要验证、或上游已经提供 checksum 时才记录 checksum。

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

随机过程记录 seed 或能够重建随机状态；外部 reference database / genome / annotation 的版本必须在会影响结果时固定。

## 7. QC 不等于删数据

QC 先产生诊断，再按 Design 中预先定义或科学上可辩护的规则决定 exclusion / correction。结果可见后新增的 exclusion rule 必须标成 post hoc，并进入 sensitivity analysis，而不是覆盖原规则。

QC 至少考虑当前 assay 的关键失败模式；例如 sequencing 的 read quality / contamination / depth / mapping，仪器的 calibration / drift，问卷的 impossible values / duplicate records。不存在统一 QC checklist 能替代 assay-specific 判断。

## 8. 数据冻结与可分析版本

用于 primary / confirmatory Analysis 的输入应有明确 data freeze，例如 Git-tracked manifest、版本目录、repository release 或其他稳定 snapshot。冻结后：

- raw 不覆盖；
- curated 修正形成新版本；
- primary analysis 使用哪个 freeze 必须明确；
- freeze 后发现的数据问题记录 amendment，并判断是否影响 confirmatory status。

大型或受控数据是否进入 Git、外部存储或远程仓库由项目实际约束决定；Skill 不默认要求把所有 raw binary 纳入 Git。

## 9. 安全与受控数据

受控人类数据、个人信息、临床数据或其他敏感数据遵守其 consent、DUA、伦理审批和存储边界。科研数据库只保存完成任务所需的最少 metadata / pointer；不要为了方便检索把受限 raw data、身份信息或凭据复制进不合适的 artifact。

## 10. 完成条件

进入 `ANALYSIS` 前至少满足：

1. 当前分析输入的数据身份、来源和版本可确认；
2. raw / curated / derived 边界清楚，raw 未被静默覆盖；
3. sample mapping 与 unit of inference 可解释；
4. 关键 metadata、missingness 与 exclusion provenance 已记录；
5. primary analysis 所需 input freeze 已明确；
6. 从 input 到 analysis-ready artifact 的变换可以重建；
7. access / ethics / privacy 条件允许当前分析实际执行。

若任何必需原始数据或访问授权仍由用户/机构掌握且当前不可获得，就在这里形成 blocker；这是需要人类介入的真实边界，而不是让 Agent用近似数据继续。
