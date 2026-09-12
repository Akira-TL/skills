# Research Tree Model

本模型是项目内部的科研进程表示，不是新的科学方法论。对象名称沿用通常科研概念；文件、Dataset、代码等 provenance 优先映射现有标准，而不是全部升格为科研节点。

## Scientific nodes

首版只把会改变科学推理结构的对象作为候选节点：

```text
objective
question
hypothesis
design
study
analysis
observation
claim
```

并非每个研究都必须出现全部类型。探索性或描述性研究可以没有 formal Hypothesis；已有公开数据的项目可以没有本项目自己的 Study。

节点最小信息：

```text
id
kind
label
parent
spawned_from
workflow_status
scientific_scope
linked_objects
created_at
closed_at
closure_reason
```

`scientific_scope` 用于保存该对象实际覆盖的人群、系统、时间、条件或其他必要边界，不承担完整科研正文。Node 进入 `closed` 时必须保存 `closure_reason`；关闭只表示当前 workflow 不再继续，不等于该科学对象被证伪。

## Resources and provenance objects

下列对象默认作为 resource / provenance object，而不是主树节点：

```text
Paper
Dataset
Sample
File
Code
Figure
Table
Model
Protocol
Software
Instrument
```

当某个 resource 本身成为独立科学问题时，可以由 Question 指向它，但不因为存在文件就创建 Tree Node。

研究对象与 provenance 的底层关系优先兼容 W3C PROV 的 `Entity / Activity / Agent` 思路；具体结构由 `study`、`data`、`analysis` 等 Skill 维护。

## Edges

结构父边用于形成可读主树；横向 Edge 表达真实科研关系。至少记录：

```text
source
relation
target
basis
created_at
```

`basis` 指向 Observation、论文、Analysis result、Design decision 或其他 canonical source。没有 basis 的箭头不能作为科学结论依据。

Evidence 默认是有依据的关系，而不是单独实体。例如：

```text
Observation O1 --supports--> Hypothesis H1
Observation O1 --weakens--> Hypothesis H2
Claim C1 --spawns--> Question Q2
```

## Git execution topology

Question / Design / Study / Analysis 发生真实科研路线分叉时，可以绑定一个规范 Git branch；命名、merge 和 archival tag 由 [`GIT-BRANCHES.md`](GIT-BRANCHES.md) 统一定义。Git graph 保存代码/配置的执行演化，Research Tree 保存科学语义；参数级执行由 Analysis Attempt + commit 表达，不升格为 Tree Node。

## Active path

Active path 是 Root 到当前 primary active Node 的主要结构路径，只用于恢复当前研究焦点，不表示其他 open branch 已被否定。多个分支可以并行执行，但总 Router 必须能指出当前 primary branch 与切换理由。
