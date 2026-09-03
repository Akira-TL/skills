---
name: akira-analysis
description: 执行可重建、可审计的科研分析；当 akira-research 已确定需要使用 Python、R、命令行统计/生信工具、机器学习、富集分析或绘图来回答一个明确科研问题时使用。
---

# Akira Analysis

`akira-analysis` 负责**怎么可靠执行分析**。科研问题、estimand、confirmatory / exploratory 边界与结果能支持什么 Claim 由 `akira-research` 决定；研究分叉归属由 `research-tree` 决定。

## 1. 接收分析任务

执行前明确：

- 当前 Question / Active Uncertainty；
- owning research-tree Node（若项目启用 research-tree）；
- Dataset identity 与输入位置；
- unit of inference；
- 目标 Analysis 是 confirmatory、sensitivity 还是 exploratory；
- 需要交付的结果、诊断与图。

缺少会改变统计含义的关键信息时，返回 `akira-research` 解决；不要用工具默认值替代科研设计决定。

## 2. Docs-first

任何会影响结果含义的工具行为都以**当前安装版本与权威文档**为准。包 API、默认参数、统计方法、输入要求、版本差异或命令语法不确定时，先检查本地版本与 `--help` / package help，再查官方 documentation / vignette / method paper；不能根据记忆猜测。

详细规则按需读取 [`references/DOCS-FIRST.md`](references/DOCS-FIRST.md)。Python 任务读取 [`references/PYTHON.md`](references/PYTHON.md)，R 任务读取 [`references/R.md`](references/R.md)。

完成标准：关键方法、默认值和参数已经与实际版本对应，任何主动偏离都有可解释理由。

## 3. 建立可重建执行入口

分析必须有一个可重复运行的入口，显式连接：

```text
input → code / command → parameters → environment → outputs
```

探索可以使用 Notebook / interactive R，但进入科研 evidence 的关键结果必须能够从脚本、workflow 或明确命令重新生成。

环境、随机性、路径与输出规则按需读取 [`references/EXECUTION.md`](references/EXECUTION.md)。

## 4. 运行与诊断

先执行与科研问题对齐的 analysis，再检查足以改变结论的失败模式。工具成功退出不等于统计模型有效；至少根据当前方法检查输入假设、样本结构、收敛、批次、缺失、异常值、随机划分、过拟合、数据泄漏和适用的 sensitivity。

当存在多个合理方法或 pipeline 时，可以全部执行；每个分析必须说明它回答的科学问题和与其他分析的关系。不要用 `v1 → v9` 作为科研结构，也不要因某个版本更显著或图更漂亮而选为最终证据。

## 5. 分析分叉与收敛

一次参数微调、软件兼容修复或等价实现保持在同一 Analysis provenance 中。以下变化通常需要作为新的 Analysis / research-tree branch：

- scientific question / estimand 改变；
- population 或 unit of inference 改变；
- confirmatory target 改变；
- 结果后出现新的 subgroup、mechanism 或 prediction；
- 方法回答的是不同问题，例如 differential abundance 与 prediction。

合理替代 pipeline 用于 sensitivity 时保留其结果。最终 preferred analysis 必须按 scientific alignment、正确推断单位、measurement/data model、diagnostics、leakage/overfitting、robustness 与 interpretability 说明选择理由；显著性或视觉吸引力不能成为选择依据。

## 6. 结果与 artifact

结果文件、模型、图片和中间数据按可重建性与体积决定是否进入 Git。大型 artifact 可以外置，但必须保留 input、producer、parameters、environment、path 与 owning research node / Analysis pointer。图形应由代码从已登记结果生成；手工修改若会改变科学表达，必须可追溯。

`akira-analysis` 不自行升级 Hypothesis / Claim。完成后把 Observation、diagnostics、sensitivity boundary、artifact pointers 与 reproduction entrypoint 返回 `akira-research` 做 Interpretation，并同步给 `research-tree` 更新节点关系。

## 7. 方法专属注意事项

DESeq2、LEfSe、KEGG、Random Forest 等方法的规则不复制成容易过期的教程。遇到具体方法时先执行 Docs-first，再根据当前版本和科研问题建立方法检查清单；只有经过多次项目验证且长期稳定的高风险注意事项才沉淀到本 Skill 的 method reference。

完成标准：最终报告能说明“运行了什么、为什么这样运行、能否重建、哪些替代方案改变结论、结果只能支持到什么范围”。
