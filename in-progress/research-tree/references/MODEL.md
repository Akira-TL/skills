# Research Tree Model

## Node

每个 Node 是可独立研究、讨论、验证或关闭的科研对象。最小字段：

```text
id
kind
label
parent
spawned_from
status
current_question_or_claim
linked_objects
created_at
closed_at
```

`kind` 首版允许：`objective`、`question`、`hypothesis`、`design`、`dataset`、`analysis`、`observation`、`claim`、`interpretation`、`communication`。

只在该对象会改变研究结构时建 Node。单篇论文、单张图、单个脚本、一次参数修改默认作为 linked artifact / evidence，不自动成为 Node。

## Edge

结构父边保证主树可读；横向 Edge 表达科学关系。Edge 至少记录：

```text
source
relation
target
basis
created_at
```

`basis` 必须指向产生该关系的讨论、evidence、analysis result 或 canonical research object，避免只保存无依据的箭头。

## Active path

Active path 是 Root 到当前 active Node 的一条结构路径。它用于恢复“现在正在研究哪一支”，不表示其他 open branch 被否定。

新结果出现后，允许 active path 跳到另一个 open branch；切换理由应是信息增益、依赖解除或用户优先级变化，而不是顺序编号。
