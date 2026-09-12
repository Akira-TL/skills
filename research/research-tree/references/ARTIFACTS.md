# Research Tree Artifact Boundary

## Git-tracked by default

适合 Git 的科研资产：

- `src/`、`scripts/` 下的科研代码与小型配置；
- `RESEARCH.md`、Literature 人类阅读 Markdown、Research / Design / Hypothesis / Analysis 等关键文本；
- `research.sqlite`、freeze manifest、环境锁定文件、运行入口；
- 小型 canonical result、绘图输入表与需要长期审计的表格。

## External / ignored by default when large

可放在外部存储或 Git 忽略目录：

- 论文 PDF/XML/HTML、supplement 等机器原始 artifact；
- 大型 raw / curated / derived data；
- 大型模型；
- 大批中间矩阵；
- 可从代码重建的图片、PDF 图形和临时结果；
- `.research/analysis/**/outputs|logs` 等 Attempt 可重建执行产物。

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
