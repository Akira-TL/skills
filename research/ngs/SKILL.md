---
name: ngs
description: 为 Akira Research 执行高通量测序（Next-Generation Sequencing, NGS）领域计算；当 data 或 analysis 处理 BCL、FASTQ、BAM/CRAM、VCF、表达矩阵、峰集、ASV/分类谱等测序数据，或需要 assay-specific QC、reference/database、pipeline execution 与 provenance 时使用。
---

# NGS

`ngs` 是 Akira Research 的测序领域执行层，不是新的科研阶段。它接受 `study`、`data` 或 `analysis` 已经确定的科学上下文，把 assay-specific 的输入检查、参考资源、流程选择、运行前检查、计算执行和 execution provenance 接回 Akira 的 Dataset / Analysis provenance；科学问题、estimand、确认性边界与 Claim 仍由上层科研 Skill 决定。

## 1. 先确认当前所有者与对象边界

进入本 Skill 时先确认 owning Skill、Research Question / Active Uncertainty、Dataset / Study identity、sample mapping、unit of inference，以及当前任务属于结果前数据处理、确认性 Analysis、sensitivity 还是 exploratory computation。

边界不清时读取 [`references/BOUNDARIES.md`](references/BOUNDARIES.md)。真实建库、测序仪运行和实验偏差属于 `study`；raw → curated / derived / analysis-ready 的测序处理属于 `data`；回答 target contrast 或进行探索性推断属于 `analysis`；生物学解释和 Claim 升级返回 `interpretation`。

完成标准：能够明确说出本轮生成的是 Dataset-derived artifact、Analysis result，还是仅执行/资源 provenance，且不会把计算产物自动解释为科学结论。

## 2. 识别 assay 与上游能力

根据实际输入与 assay 选择最窄执行通道。需要查看官方 OpenAI `ngs-analysis` 的 assay-specific 规则、runner、registry、resource gate 或 run envelope 时读取 [`references/UPSTREAM.md`](references/UPSTREAM.md)，并从运行时 source view `~/.agents/external/ngs-analysis/` 读取对应原始文件；不要把第三方 Skill 正文复制进 Akira 自研 Skill。

执行前核验运行时 source view 与其 `.codex-plugin/plugin.json`。source view 不存在或目标 runner/registry 缺失时，把它作为执行环境 blocker 返回 owning Skill；不要从模型记忆重建 upstream 参数或默认值。

完成标准：assay、输入层级、选用的 upstream lane / runner 与必要 reference/database 已明确，且实际读取了会影响执行的当前 upstream 文件。

## 3. 科研方法决定先于软件自动选择

`ngs` 可以比较可行工具、检查依赖和执行已经选定的方法，但不以“当前安装了什么软件”替代科研方法判断。

- `data` 所有的 QC、filter、trimming、alignment、quantification、variant/peak/taxonomy calling 先按 assay failure mode 与结果前规则决定，再交给 runner 执行；任何改变样本或特征含义的处理都保留 provenance。
- `analysis` 所有的模型、design formula、contrast、normalization、covariate、multiple-testing family 与 sensitivity 由 `analysis` 依据 Design / estimand / dependence structure 决定；upstream 的 `auto` 方法只能用于明确的 feasibility / exploratory convenience，不能替代确认性 Analysis 的方法冻结。
- 受控人类数据的 consent、DUA、伦理与存储边界由 `data` / 项目约束决定，优先级高于 upstream 的 cloud 或 upload convenience。

完成标准：执行参数能够追溯到科学/数据决定，而不是由软件可用性、默认值或显著性结果反向决定。

## 4. Preflight、资源与执行

先使用 upstream 当前版本提供的 preflight、pipeline registry、reference/database registry 与 resource gate 检查本机工具和资源，再决定是否执行。缺少软件时先形成可审阅 install plan；缺少 reference/database 时先形成 resource readiness / setup plan。安装、下载、专有许可、账户登录或 cloud upload 需要额外授权时保持显式 blocker。

运行后按 [`references/RUN-ENVELOPE.md`](references/RUN-ENVELOPE.md) 把 upstream run envelope 映射到 Akira provenance。run envelope 是计算执行证据，不替代 `research.sqlite` 中 Dataset / Analysis 的科学身份与时序关系。

完成标准：input → command/workflow → parameters → environment/resources → outputs 可重建，失败、warning、样本丢失和部分输出不会被静默吞掉。

## 5. 返回 owning Skill

返回至少包含：

```text
assay / upstream lane
input Dataset / Study pointer
reference/database identity and version
executed command / workflow entrypoint
run envelope path
QC / validation boundary
produced Dataset-derived or Analysis artifacts
sample / feature exclusions or deviations
execution blockers or caveats
```

若本轮属于 `data`，由 `data` 决定 Dataset identity、freeze 与是否已经 analysis-ready；若属于 `analysis`，由 `analysis` 登记 Analysis result、diagnostics 与 Observation，再交给 `interpretation`。`ngs` 不自行生成 causal / mechanistic Claim，也不因为 pipeline 成功完成就宣布科研问题已经解决。
