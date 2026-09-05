# Research Tree Artifact Boundary

## Git-tracked by default

适合 Git 的科研资产：

- 分析/处理代码与小型配置；
- Research / Design / Hypothesis 等关键文本；
- freeze manifest、环境锁定文件、运行入口；
- 小型结果摘要与需要长期审计的表格。

## External / ignored by default when large

可放在外部存储或 Git 忽略目录：

- 大型 raw / curated / derived data；
- 大型模型；
- 大批中间矩阵；
- 可从代码重建的大量图片和临时结果。

外部不等于无 provenance。至少保存：

```text
artifact identity
path / URI
role
source
version / acquisition batch
producer code / workflow
input artifacts
owning research node
created_at
why git tracking is not required
```

如果 artifact 是确认性 Analysis 的输入或冻结条件，仍必须满足 `akira-research` 对 Dataset / Analysis freeze 的要求；“文件太大不进 Git”不能绕过结果前 provenance。
