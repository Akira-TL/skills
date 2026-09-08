# data

`data` 管理从 raw 到 curated、derived 和 analysis-ready 的 Dataset 身份、metadata、QC、sample mapping、artifact provenance 与 freeze 边界。

Dataset 表示进入数据管理的对象，不替代产生这些数据的 Study，也不替代后续 Analysis。大型数据可以保存在外部位置，但其稳定 identity、版本、来源和与 Analysis 的时序关系必须可追溯。

高通量测序（Next-Generation Sequencing, NGS）数据需要 BCL/FASTQ 处理、read QC、alignment、quantification、variant/peak/taxonomy calling、reference/database 或其他 assay-specific pipeline 时，由 `data` 调用 `ngs` 执行；NGS runner 负责计算事实，Dataset identity、sample mapping、QC/exclusion timing、raw/curated/derived 与 freeze 仍由 `data` 决定。
