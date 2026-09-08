# NGS Run Envelope → Akira Provenance

OpenAI `ngs-analysis` 的 run envelope 记录一次计算执行事实；Akira 的 `research.sqlite` 记录该执行在科研项目中的 Dataset / Analysis 身份、科学目标与时序关系。两者互补，不互相替代。

## 运行产物映射

典型 upstream envelope：

```text
run_manifest.json
config.json
validation/
logs/
versions/software_versions.json
manifest/lineage.tsv
artifact_index.json
summary.md
resources/
visualizations/
```

映射原则：

| Upstream artifact | Akira 用途 |
| --- | --- |
| `run_manifest.json` | execution Activity、runner / workflow、开始结束状态、主要输入输出 pointer |
| `config.json` | 参数与已选择 execution specification |
| `validation/` | 输入/preflight/QC 的机器证据，不自动构成科学 Observation |
| `logs/` | 命令、warning、failure、stderr/stdout 的逐字 execution evidence |
| `versions/software_versions.json` | 软件/环境版本 provenance |
| `manifest/lineage.tsv` | input → output lineage；与 Sample / Dataset mapping 对接 |
| `artifact_index.json` | run-local artifact inventory；其中 checksum 作为 upstream 自身完整性记录即可 |
| `summary.md` | upstream 的执行摘要，不作为 Akira canonical scientific conclusion |
| `resources/` | reference/database readiness、bundle identity、下载/缺失状态 |
| `visualizations/` | QC/diagnostic 或 Analysis visualization；语义由 owning Skill 决定 |

## Dataset-owned run

当 owning Skill 为 `data`：

1. 先有输入 Dataset / Study pointer 与 sample identity；
2. runner 产生 curated / derived artifact；
3. `data` 记录 transformation entrypoint、reference/database version、run-envelope pointer 与 sample/feature exclusion provenance；
4. 需要成为 primary/confirmatory Analysis input 时，再由 `data` 建立稳定 analysis-ready Dataset / freeze；
5. run envelope 内的 QC 指标不因存在统计图或阈值就自动成为项目科学 Observation。

例如 FASTQ → Salmon count matrix、BAM → VCF、FASTQ → peak set、FASTQ → ASV table 都首先形成 derived Dataset。

## Analysis-owned run

当 owning Skill 为 `analysis`：

1. 在第一次结果生成前先按 `analysis` 契约登记 Analysis plan；确认性 Analysis 完成正式 freeze；
2. 把已冻结的 method / formula / contrast / parameters 交给 upstream runner；
3. run envelope 记录实际 execution；
4. 结果 table、estimate、diagnostics、sensitivity 与 figure 作为 Analysis artifacts 登记；
5. 由 `analysis` 从具体结果 artifact 形成项目 Observation，再交给 `interpretation`。

如果 upstream runner 自动选择的方法与结果前 Analysis plan 不一致，停止并形成 amendment / new Analysis；不能把自动选择事后写回成原计划。

## Checksum 与 Git

upstream 可以为 `artifact_index.json` 计算 SHA256，这是其 run envelope 的内部完整性能力。Akira 不因此要求把同一 checksum 再复制进 `research.sqlite`，也不把“缺少 checksum”升级为一般科研 completion blocker。Dataset / Analysis 是否进入 Git 仍按 Akira 的 artifact、体积、可重建性、受控数据与 freeze 契约决定。

## Failure boundary

以下情况必须返回 owning Skill 处理，而不是把 run 标记成科研完成：

- input/sample mapping 不一致；
- reference/database identity 不匹配或资源不完整；
- runner 部分成功但丢失样本/contrast/feature；
- warning 会改变 estimand、测量有效性或统计解释；
- tool/software fallback 改变原冻结方法；
- QC 暴露了需要新增 exclusion rule 的结果后决策；
- 生成文件存在，但关键 validation / lineage / environment provenance 缺失。
