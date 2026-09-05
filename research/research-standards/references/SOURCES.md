# Authoritative Standards Sources

本文件只保存“去哪类权威来源核验”的稳定索引，不复制会随版本变化的 checklist。实际执行时检查当前正式版本与适用范围。

## General rigor

- NIH rigor and reproducibility guidance：用于一般科研严谨性、可重复性与研究过程要求；不替代具体学科方法。

## Reporting guidelines

- EQUATOR Network：按 study design 查找适用 reporting guideline。
- CONSORT：随机对照试验报告。
- SPIRIT：临床试验 protocol 报告。
- STROBE：观察性研究报告。
- PRISMA：系统综述与 meta-analysis 报告。
- ARRIVE：动物实验报告。

报告规范只约束报告完整性与透明度；若其官方 scope 没有同时规定研究设计或方法学，不把它扩张为方法学标准。

## Metadata and study/assay description

- ISA（Investigation–Study–Assay）：生命科学 Investigation / Study / Assay、sample-to-data 与相关 metadata 描述。
- GSC MIxS 及适用 checklist（例如 MIMARKS）：基因组、宏基因组、marker-gene 等领域 minimum-information metadata。

## Provenance and research objects

- W3C PROV：Entity / Activity / Agent 与 provenance relations。
- FAIR Principles：Findable、Accessible、Interoperable、Reusable 数据与 metadata 原则。
- RO-Crate：需要打包数据、代码、软件、结果和上下文 metadata 时采用其 Research Object 描述方式。

## Method and software

统计、实验、生物信息或机器学习方法优先核验方法学论文、正式指南或领域共识；具体软件 API、命令、参数、默认值和版本差异再核验该软件当前官方 documentation / vignette / `--help`。二者不能互相替代。
