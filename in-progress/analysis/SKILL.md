---
name: analysis
description: 执行可重建、可审计的科研分析；当已有可分析 Dataset，需要用统计、生物信息、Python、R、机器学习、富集分析或绘图回答明确 Research Question、估计 target contrast、执行 sensitivity 或探索新模式时使用。
---

# Analysis

`analysis` 同时管理科研分析语义与具体计算执行。Research Question 与 active branch 来自 `akira-research` / `research-tree`；本 Skill 负责让分析目标、统计方法、代码、环境、诊断和结果边界彼此一致。

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

任何关键实现行为不确定时实际查证，不凭记忆猜测。详细规则见 [`references/DOCS-FIRST.md`](references/DOCS-FIRST.md)；Python 读取 [`references/PYTHON.md`](references/PYTHON.md)，R 读取 [`references/R.md`](references/R.md)。

## 3. 建立可重建执行入口

关键结果必须能从以下链条重建：

```text
input → code / command → parameters → environment → outputs
```

Notebook / interactive session 可以用于探索，但进入 scientific evidence 的结果必须有脚本、workflow 或明确命令入口。环境、随机性、路径和输出约定见 [`references/EXECUTION.md`](references/EXECUTION.md)。

## 4. 运行、诊断与合理替代分析

先运行与 scientific target 对齐的分析，再检查足以改变结论的 failure mode。工具成功退出不等于模型有效。

多个合理方法或 specification 可以并存，但必须说明各自回答什么问题。参数微调、兼容修复和等价实现保留在同一 Analysis provenance；scientific question / estimand、population、unit of inference 或 confirmatory target 改变时，通常形成新的 Analysis / research-tree branch。

Sensitivity 的目的用于判断结论对合理分析选择是否稳定，不用于寻找显著结果。Preferred analysis 的选择依据是 scientific alignment、推断单位、measurement/data model、diagnostics、leakage/overfitting、robustness 与 interpretability，而不是 `P` value 或图形吸引力。

## 5. 结果、图和大型 artifact

结果文件、模型、图片和中间矩阵根据体积、可重建性和项目约束决定是否进入 Git。大型 artifact 可以外置，但必须保留 input、producer、parameters、environment、version、path 和 owning Analysis / research node。

分析图用于诊断或呈现 analysis result 时属于本 Skill；面向论文的 panel 组合、版式与传播表达交给 `communication`，但必须从已登记结果派生。

## 6. 返回科学结果

`analysis` 产生 Observation / estimate、uncertainty、diagnostics、sensitivity boundary、artifact pointers 和 reproduction entrypoint，不自行把结果升级成 causal / mechanistic Claim。科学解释交给 `interpretation`，研究分叉更新交给 `research-tree`，下一步由 `akira-research` 决定。

完成标准：能明确说明运行了什么、为什么适用、如何重建、合理替代分析是否改变结论、结果直接显示什么以及哪些科学解释仍超出当前 Analysis 的支持范围。
