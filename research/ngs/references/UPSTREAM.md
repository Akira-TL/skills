# OpenAI NGS upstream 边界

## Source of truth

第三方执行源由 Akira Lattice 以独立 Git submodule 管理：

```text
skills/openai-plugins
└── plugins/ngs-analysis
```

运行时通过只读 source view 暴露：

```text
~/.agents/external/ngs-analysis
```

该目录应直接指向 Lattice submodule 中的 `plugins/ngs-analysis`。每次使用前读取：

```text
~/.agents/external/ngs-analysis/.codex-plugin/plugin.json
```

以其中当前 `name`、`version`、`license` 与目录结构为准。Akira 不复制第三方 Skill 正文；需要 assay-specific 细节时直接读取当前 upstream 文件。

当前首次接入固定于 OpenAI `plugins` repository commit `1e285826e604f66f7208f7ac4dba0fe8341d1f57`，其中 `ngs-analysis` 为 1.0.3。后续升级通过 submodule pointer 显式发生，不把“最新 upstream”自动漂移进科研执行。

## Upstream lane map

根据实际任务按需读取最窄 Skill：

```text
skills/ngs-analysis-router/SKILL.md
skills/ngs-runtime-env/SKILL.md
skills/ngs-bcl-to-fastq/SKILL.md
skills/ngs-fastq-qc/SKILL.md
skills/ngs-bulk-rnaseq/SKILL.md
skills/ngs-bulk-rnaseq-counts-qc/SKILL.md
skills/ngs-bulk-rnaseq-differential-expression/SKILL.md
skills/ngs-scrna-seq/SKILL.md
skills/scrna-seq-qc/SKILL.md
skills/ngs-dna-variant-calling/SKILL.md
skills/ngs-dna-germline-variants/SKILL.md
skills/ngs-dna-somatic-variants/SKILL.md
skills/ngs-dna-umi-panel-variants/SKILL.md
skills/ngs-epigenomics-peaks/SKILL.md
skills/ngs-atacseq-peaks-qc/SKILL.md
skills/ngs-chip-cutrun-peaks-qc/SKILL.md
skills/ngs-amplicon-microbiome/SKILL.md
skills/ngs-shotgun-metagenomics/SKILL.md
```

通用结构化资料按需读取：

```text
references/intake-schema.json
references/pipeline-registry.json
references/reference-registry.json
references/database-registry.json
references/run-envelope-schema.json
references/runtime-install-guidance.md
```

实际执行优先使用 upstream 已提供的 `scripts/` 与 `workflows/`；调用前读取目标 runner 的 `--help` 或源码中参数定义，不从旧会话、模型记忆或本文件缓存具体 CLI 参数。

## Akira 覆盖规则

upstream 提供 execution implementation 与 assay-specific guidance，但以下决定仍由 Akira canonical Skill 拥有：

- Research Question、Active Uncertainty 与 branch：`akira-research` / `research-tree`；
- Study / Sample / Assay 的真实发生事件：`study`；
- Dataset identity、sample mapping、QC/exclusion timing、raw/curated/derived、freeze：`data`；
- estimand、design formula、contrast、统计方法、confirmatory/exploratory、sensitivity：`analysis`；
- scientific Claim 与 evidence boundary：`interpretation`；
- 适用科研规范：`research-standards`。

当 upstream guidance 与上述 canonical 科研语义冲突时，保留 upstream 作为工具实现证据，并按 Akira scientific contract 决定是否执行、如何解释以及需要什么 amendment。

## 安装与下载

upstream 的 preflight / install plan 可以用于确定缺失工具，但实际安装、较大 reference/database 下载、专有许可、账户认证、cloud execution 或受控数据上传必须遵守当前项目与用户授权。不要因为 upstream runner 支持某条路径就推定当前项目有权限使用。
