---
name: data
description: 管理科研数据从 raw 到 curated / derived / analysis-ready 的身份、metadata、QC、sample mapping、freeze 与 provenance；当已有数据进入项目、Study 产生 raw outputs，或 Analysis 前需要确认可分析 Dataset 时使用。
---

# Data

`data` 负责“数据是什么、从哪里来、是否能被可靠分析”。Sample 的真实产生与 Assay execution 归 `study`；统计推断归 `analysis`。当 Dataset 来自高通量测序（Next-Generation Sequencing, NGS），且需要 BCL/FASTQ/BAM/CRAM/VCF、表达矩阵、峰集、ASV/分类谱等 assay-specific 处理、QC、reference/database 或 pipeline execution 时，调用 [`ngs`](../ngs/SKILL.md) 作为领域执行层；Dataset identity、raw/curated/derived、sample mapping、exclusion timing 与 freeze 仍由本 Skill 拥有。

## 1. 确认数据来源与适用规范

数据可以来自本项目 `study`，也可以是外部公开/合作/受控 Dataset。先确认稳定 identity、来源、版本、访问/伦理边界以及它为什么与当前 Research Question 有关。

调用 `research-standards` 核验适用 metadata / minimum-information、FAIR 与 provenance 要求；生命科学 sample-to-data mapping 需要与 ISA / 领域标准一致时按其正式规范记录。

## 2. 保持数据分层与身份

至少区分 raw、curated、derived，不原地覆盖 raw。Sample / participant / experimental unit identity 必须能追溯；technical replicate、aliquot、library、lane、batch、timepoint 与 biological unit 不得混淆。

完整 Dataset identity、missingness、QC、transformation、freeze、external storage 与 Git 边界见 [`references/CONTRACT.md`](references/CONTRACT.md)。

## 3. QC 与 transformation

QC 先产生诊断，再按结果前规则或科学上可辩护的规则处理 exclusion / correction。结果可见后新增的 exclusion 或 filtering 规则必须保留 timing 和 sensitivity 边界。NGS 数据的 read quality、contamination、depth、mapping、cell/feature QC 等 assay-specific failure mode 由 `ngs` 提供执行与诊断能力，但是否改变 Dataset 仍按本 Skill 的数据语义决定。

从 raw / curated 到 analysis-ready Dataset 的每一步必须可以由代码、workflow、命令或明确人工记录重建。

## 4. 冻结并交给 Analysis

Primary / confirmatory Analysis 使用的数据必须有明确 freeze 或等价稳定 snapshot。大型/受控 Dataset 不要求为了 Git 而复制进仓库；使用稳定 accession、版本、路径、manifest、外部位置和必要 provenance 保持可恢复性。

完成标准：当前 Analysis input 的身份、sample mapping、unit of inference、关键 metadata / missingness、QC、transformation 和 freeze 都可解释并可追溯；任何访问或数据质量 blocker 已明确返回总 Router。
