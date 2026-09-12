---
name: research-standards
description: 识别并核验科研项目当前适用的既有规范、指南与领域标准；当研究类型、研究实施、metadata、provenance、统计方法或报告要求会影响下一步科研工作时使用。
---

# Research Standards

`research-standards` 不制定 Akira 自有科研方法。它负责根据当前研究问题与研究类型，查找、核验并记录真正适用的既有科研规范，再把这些约束交给 `design`、`study`、`data`、`analysis`、`interpretation` 或 `communication`。

## 1. 识别当前研究情境

先从项目现有事实确定与规范选择有关的维度，例如研究设计、研究对象/领域、数据类型、主要推断目标和传播目标。只记录实际影响规范选择的维度，不为了分类完整而强行给项目贴满标签。

若研究设计或推断目标尚未确定，只记录当前已知边界，并把缺口返回 `akira-research`；不要用某个 reporting guideline 反推研究设计。

## 2. 查权威来源，而不是凭记忆套规范

适用规范必须从当前权威来源核验。优先级通常为：

1. 标准/指南维护组织的官方页面与正式规范文本；
2. 正式方法学或共识论文；
3. 学科协会、监管机构或资助机构的正式指导；
4. 只有前述来源无法回答实现细节时，才使用软件官方文档或其他次级材料。

规范名称、版本、适用范围或当前状态不确定时必须实际查证。常用规范家族与职责边界见 [`references/SOURCES.md`](references/SOURCES.md)。涉及伦理审查、人类受试者、个人/敏感数据、临床研究、动物研究、许可、跨境数据/材料或其他 institution / jurisdiction-specific requirement 时，同时读取 [`references/REGULATED-RESEARCH-AUTHORITY.md`](references/REGULATED-RESEARCH-AUTHORITY.md)：把“找到规则”和“规则是否适用于当前项目”分开，`unknown` 不得降格为 `not applicable`，也不得从用户 locale、语言、affiliation 或 manuscript wording 推断 jurisdiction、approval、waiver 或 consent。

## 3. 区分规范的职责

至少区分：

- **研究设计 / 实施指导**：约束研究如何设计或实施；
- **报告规范（reporting guideline）**：约束应完整报告什么，不自动构成研究设计方法或质量评价方法；
- **metadata / minimum-information standard**：约束样本、测定、数据与上下文元数据；
- **provenance standard**：约束 Entity / Activity / Agent 及来源关系；
- **数据管理原则**：约束可发现、可访问、互操作与可复用；
- **方法学依据**：约束具体统计、实验或计算方法的科学适用性；
- **软件实现文档**：约束当前软件版本的真实 API、参数和默认行为。

不能把一种规范越权当成另一种规范使用。例如 CONSORT / STROBE 不能代替 causal identification、sample-size planning 或统计模型选择。

## 4. 记录项目适用规范

项目只保存当前真正会影响研究工作的最小记录，至少包含：

```text
standard / guideline
role
applies_to
version_or_date (when material)
official_source
why_applicable
```

研究推进后若 study design、assay、data modality 或传播目标改变，重新核验对应规范；不把旧规范静默沿用到新分支。涉及 regulated research 时还要记录 applicability basis / state 与 formal decision maker；多个 jurisdiction / institution / funder authority 并行时分别保留，冲突或 precedence 不清则保持 unresolved，不由 Agent 平均、静默覆盖或自行选择最宽松/最严格规则。

## 5. 路由

- 研究设计、estimand、sampling、control、measurement → `design`；
- 实际 Study / Assay / protocol execution → `study`；
- dataset、metadata、QC、freeze、provenance → `data`；
- 统计/计算方法与软件实现 → `analysis`；
- evidence boundary 与 Claim → `interpretation`；
- manuscript / report / figure / table → `communication`。

完成标准：当前动作依赖的规范已经从权威来源核验，职责没有混用，且相关 Skill 能明确知道“采用什么规范、为什么适用、它约束哪部分工作”。
