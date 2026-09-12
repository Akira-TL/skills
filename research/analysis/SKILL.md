---
name: analysis
description: 执行可重建、可审计的科研分析；当已有可分析 Dataset，需要用统计、生物信息、Python、R、机器学习、富集分析或绘图回答明确 Research Question、估计 target contrast、执行 sensitivity 或探索新模式时使用。
---

# Analysis

`analysis` 同时管理科研分析语义与具体计算执行。Research Question 与 active branch 来自 `akira-research` / `research-tree`；本 Skill 负责让分析目标、统计方法、代码、环境、诊断和结果边界彼此一致。高通量测序（Next-Generation Sequencing, NGS）的 assay-specific pipeline、reference/database、preflight、runner 与 execution provenance 交给 [`ngs`](../ngs/SKILL.md)；estimand、统计方法、design formula、contrast、confirmatory / exploratory 与 sensitivity 的科研决定仍由本 Skill 拥有。

## 1. 接收科学分析目标

执行前明确：

- 当前 Research Question / Active Uncertainty；
- owning research-tree Node；
- Dataset identity、freeze 与输入位置；
- unit of inference；
- estimand / target contrast 或 exploratory objective；
- confirmatory、sensitivity、exploratory 的边界；
- 需要返回的 estimate、diagnostics、Observation 与图表。

科研分析、Design alignment、Estimate-first、sensitivity、amendment 与 Hypothesis Evaluation 的完整规则见 [`references/RESEARCH-CONTRACT.md`](references/RESEARCH-CONTRACT.md)。缺少会改变统计含义的关键信息时返回总 Router，不用软件默认值替代科研决定。

## 2. 方法依据与 Docs-first

统计/生物信息/机器学习方法的科学适用性优先核验方法学论文、正式指南或领域共识；具体软件 API、命令、参数、默认值和版本差异则核验当前官方 documentation、vignette、package help 或 `--help`。两类依据不能互相替代。

任何关键实现行为不确定时实际查证，不凭记忆猜测。详细规则见 [`references/DOCS-FIRST.md`](references/DOCS-FIRST.md)；Python 读取 [`references/PYTHON.md`](references/PYTHON.md)，R 读取 [`references/R.md`](references/R.md)。官方 documentation、`--help`、软件输出等逐字证据按 `log` / diagnostic 等机器或外部证据 artifact 保存原文，不为满足中文科研写作规范而改写其内容。

## 3. 建立可重建执行入口

关键结果必须能从以下链条重建：

```text
input → Git commit + code / command → parameters → environment → outputs
```

Notebook / interactive session 可以用于探索，但进入 scientific evidence 的结果必须有脚本、workflow 或明确命令入口。环境、随机性、路径和输出约定见 [`references/EXECUTION.md`](references/EXECUTION.md)。同一 Analysis 下每次形成可独立审阅的执行状态时使用 Analysis Attempt；Attempt 由 Git commit 固定代码版本，不复制代码快照，config/output 保持独立，完整边界见 [`references/ATTEMPTS.md`](references/ATTEMPTS.md)。任何 Analysis 在第一次运行结果生成代码前，都先以当前计划调用 `research-db record-analysis`；真正执行后再用 `research-db record-analysis-attempt` 固定具体 commit、配置与执行状态。探索性 Analysis 先登记为 `planned`，确认性 Analysis 按其 freeze 路径登记。该结果前登记会检查 Analysis plan、作为 `pre_result_support` 登记的人类科研正文，以及当前输入 Dataset / Study 的人类可读 provenance；先修正文再执行。探索性 Analysis 不因这项检查被伪装成确认性 freeze，确认性 Analysis 仍另外满足正式 freeze provenance。

## 4. 运行、诊断与合理替代分析

先运行与 scientific target 对齐的分析，再检查足以改变结论的 failure mode。工具成功退出不等于模型有效。

多个合理方法或 specification 可以并存，但必须说明各自回答什么问题。参数微调、兼容修复和等价实现通常进入同一 Analysis 下不同 Attempt；scientific question / estimand、population、unit of inference 或 confirmatory target 改变时，形成新的 Analysis / Research Tree branch。Attempt 可以从前一个 Attempt 的思路或代码演化而来，但运行时不得依赖 sibling Attempt 或其他 Analysis 的工作目录；跨 Analysis 真正共享的 Python 逻辑先提升到 `src/<project-package>/`，下游数据依赖先提升为 canonical Dataset / registered artifact。NGS upstream runner 提供的 `auto` 方法选择或软件 fallback 只能在明确的 feasibility / exploratory convenience 中使用；确认性 Analysis 必须先冻结科研方法，再让 `ngs` 执行该方法。

Sensitivity 的目的用于判断结论对合理分析选择是否稳定，不用于寻找显著结果。Preferred analysis 的选择依据是 scientific alignment、推断单位、measurement/data model、diagnostics、leakage/overfitting、robustness 与 interpretability，而不是 `P` value 或图形吸引力。

当同一 Analysis 的实现/执行优化存在稳定、可重复的机械指标时，可以按 [`references/ATTEMPTS.md`](references/ATTEMPTS.md) 使用受控迭代：结果前固定 baseline、metric、方向、target 和 guard，每个 Attempt 只做一个可解释的主要变化，并同时保留改善与未改善/失效路线的原因。该模式不能用单一分数替代 scientific validity，也不能让第三方 controller 接管科研 branch 的 Git commit/revert 生命周期。

## 5. Python 计算与 R 绘图的默认边界

默认科研计算语言是 Python：数据读取、QC、整理、统计推断、模型、敏感性分析和正式结果表由 Python 完成。项目级共享 Python 代码采用 `pyproject.toml + src/<project-package>/`，具体 Analysis entrypoint 放 `scripts/analyses/`，使用 package absolute import，不使用 `sys.path` hack 或跨 Analysis import。

R 默认只承担可视化：`scripts/figures/*.R` 读取 Python 已登记生成的机器可读结果表/plotting table，再生成图。不要使用 `rpy2` 把两个运行时耦合；R 绘图阶段不重新进行 sample filtering、normalization、model fitting、effect estimation、显著性检验或 multiplicity adjustment，显著性标记等统计结果也由 Python 结果表提供。只有存在明确方法学理由、成熟关键实现主要位于 R/Bioconductor，或用户明确要求时，R 才承担统计分析；这种例外必须保存完整 R 方法 provenance，而不是把 Python-first 当成 Python-only。详细语言边界见 [`references/PYTHON.md`](references/PYTHON.md) 与 [`references/R.md`](references/R.md)。

## 6. 结果、图和大型 artifact

结果文件、模型、图片和中间矩阵根据体积、可重建性和项目约束决定是否进入 Git。`.research/analysis/<analysis>/<attempt>/outputs|logs` 是机器执行区，默认不进 Git；代码、config、Markdown 与需要长期审计的小型 canonical result 进入 Git。大型/可重建 artifact 可以外置或 ignore，但必须保留 input、producer、parameters、environment、version、path 和 owning Analysis / research node。

分析图用于诊断或呈现 analysis result 时属于本 Skill；面向论文的 panel 组合、版式与传播表达交给 `communication`，但必须从已登记结果派生。默认图形二进制文件可重建，因此项目初始化时忽略常见生成图格式；真正需要 Git 审阅的例外由 artifact provenance 显式纳入。

## 7. 返回科学结果


`analysis` 产生 Observation / estimate、uncertainty、diagnostics、sensitivity boundary、artifact pointers 和 reproduction entrypoint，不自行把结果升级成 causal / mechanistic Claim。科学解释交给 `interpretation`，研究分叉更新交给 `research-tree`，下一步由 `akira-research` 决定。

完成标准：能明确说明运行了什么、为什么适用、如何重建、合理替代分析是否改变结论、结果直接显示什么以及哪些科学解释仍超出当前 Analysis 的支持范围。
