---
name: study
description: 记录研究实际实施过程；当 frozen Design 已进入真实采样、实验、观察、Assay 或其他数据产生阶段，需要保存实际 protocol、Sample/Assay、deviation、batch、失败和实施 provenance 时使用。
---

# Study

`study` 负责“实际上做了什么”。计划属于 `design`；Dataset 整理与 QC 属于 `data`；统计与计算推断属于 `analysis`。高通量测序（Next-Generation Sequencing, NGS）的真实提取、建库、测序仪运行、lane/run 与偏差在这里记录；BCL/FASTQ 等 raw output 交给 `data`，后续 assay-specific 计算由 `data` 或 `analysis` 调用 `ngs`。

## 1. 读取 Design 与适用规范

若项目有 frozen Design，先读取其 sampling、groups、measurements、controls、protocol 与结果前边界。没有本项目 Design 的既有数据研究可以不进入本 Skill。

调用 `research-standards` 核验当前研究类型、Assay 和 metadata 需要遵守的领域标准。生命科学 Study / Assay / sample-to-data metadata 优先参考 ISA 及领域 minimum-information standard；provenance 关系优先兼容 W3C PROV。

## 2. 记录实际实施

对每次真实研究实施，明确记录实际发生的：

```text
study identity
source / participant / experimental unit
sample collection and processing
actual groups / exposure / intervention
assay / measurement execution
protocol and material versions
instrument / operator / software when material
batch / run / plate / time
failures / missing events
deviations from design
outputs and their locations
```

Sample identity 在这里首次产生或确认时保持稳定；后续 `data` 引用这一身份，不另造一套 Sample identity。

## 3. Design 与 execution 分离

实际实施偏离 Design 时，保留 frozen Design，并记录 deviation 的内容、原因、时间、受影响单位以及是否可能改变 estimand、measurement validity、bias 或后续 Analysis。不能修改旧 Design 来让计划看起来与实际一致。

若偏离已经改变 scientific target 或 identification，返回 `akira-research`，由总 Router 决定进入新的 `design`、`hypothesis` 或其他研究分支。

## 4. Provenance 与产物交接

Study 中的真实过程优先表达为 provenance Activity；Sample、specimen、raw output 等作为可追踪 Entity，并记录执行相关 Agent / instrument。项目级 `research.sqlite` 已结构化保存 Study、Sample、Assay、deviation 与 Study artifact；数据库契约与完成门禁由 [`akira-research/RESEARCH-DB.md`](../akira-research/RESEARCH-DB.md) 统一维护，语义仍以实际发生事件为准。

实际生成的 raw data / files 交给 `data` 建立 Dataset identity、QC、curation 与 freeze；本 Skill 不把“数据文件存在”解释成 scientific evidence。

完成标准：计划和实际实施能够明确区分，所有影响后续推断的 Sample / Assay / deviation / batch / failure 都可追溯，且 raw outputs 能无歧义交给 `data`。
