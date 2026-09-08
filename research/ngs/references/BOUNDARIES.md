# NGS 在 Akira Research 中的对象边界

NGS 只提供测序领域计算能力；对象归属仍由 Akira Research 的 `study`、`data`、`analysis` 与 `interpretation` 决定。

| 动作 | owning Skill | 典型产物 |
| --- | --- | --- |
| 样本采集、提取、建库、测序仪实际运行、lane/run deviation | `study` | Study / Sample / Assay / raw instrument output pointer |
| BCL → FASTQ、demultiplexing | `data → ngs` | curated/derived FASTQ Dataset |
| FASTQ inventory、read QC、trimming | `data → ngs` | QC artifact、curated FASTQ |
| alignment / mapping | `data → ngs` | BAM/CRAM 或等价 derived Dataset |
| transcript/gene quantification | `data → ngs` | count / abundance matrix |
| variant calling | `data → ngs` | VCF/BCF derived Dataset |
| peak calling / consensus peak construction | `data → ngs` | peak-set derived Dataset |
| ASV/OTU inference、taxonomy / functional profiling | `data → ngs` | feature / taxonomy / function profile |
| cell-level technical QC 与预定义 exclusion | `data → ngs` | curated single-cell Dataset |
| clustering、UMAP、marker exploration | `analysis → ngs` | exploratory Analysis artifacts |
| differential expression / accessibility / binding / abundance | `analysis → ngs` | estimate、uncertainty、diagnostics、result table |
| enrichment / pathway / association / sensitivity | `analysis → ngs` | Analysis result / sensitivity artifact |
| 结果的生物学含义、因果/机制层级、Claim | `interpretation` | evidence-bounded Claim |

## 判断原则

同一工具可以在不同语义层承担不同角色，不能只按软件名分类。例如 normalization 如果只是生成预先定义的 analysis-ready representation，可属于 Dataset transformation；如果 normalization choice 是多个合理统计 specification 的一部分并用于判断结论稳定性，则属于 Analysis / sensitivity。

判断时依次问：

1. 这一步是否记录真实实验/测序发生了什么？是则属于 `study`。
2. 这一步是否主要把原始测序信号转换成稳定、可追溯的分析输入，而不回答组间/条件间科学 contrast？是则属于 `data`。
3. 这一步是否估计、检验、预测或探索 Research Question 对应的统计结构？是则属于 `analysis`。
4. 这一步是否把结果升级成 descriptive / association / causal / mechanistic Claim？是则属于 `interpretation`。

边界出现重叠时保留实际 provenance：一个 `data → ngs` runner 可以产生供后续 `analysis` 使用的诊断图，但这些图不能因为“看起来有组间差异”就被当成正式 Analysis result。
