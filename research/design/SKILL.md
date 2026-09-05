---
name: design
description: 把 Research Question、Hypothesis prediction 或其他明确 scientific target 转成可识别、可执行的研究设计；当需要定义 estimand、sampling、comparison、measurement、controls、precision、decision boundary 或 protocol 前置条件时使用。
---

# Design

`design` 负责“准备怎样研究”，不负责记录实际发生了什么。具体 Study / Assay 执行交给 `study`，数据整理交给 `data`，统计实现交给 `analysis`。

## 1. 读取科学目标与适用规范

从 `research-tree` 取得当前 Research Question / Active Uncertainty；有 Hypothesis Set 时读取其 discriminator / predictions，但不要求所有研究都必须先有 Hypothesis。

根据研究类型调用 `research-standards` 核验适用的 design/conduct、领域与 reporting guidance。Reporting guideline 只用于提前确保必要信息会被设计和记录，不代替设计方法本身。

## 2. 先定义 estimand / target contrast

在选择实验技术前明确 population / system、exposure / intervention / condition、comparator、outcome / measurement、time、unit of inference，以及真正要识别的 estimand / target contrast。

完整 identification、measurement validity、bias protection、sample-size / precision 与 decision-boundary 规则见 [`references/CONTRACT.md`](references/CONTRACT.md)。

## 3. 形成可执行设计

设计至少覆盖与当前问题有关的 sampling、groups / comparator、measurement / assay plan、controls、主要 analysis alignment、precision rationale、ethics / access / feasibility，以及结果前需要冻结的 primary / confirmatory 边界。

存在真实 feasibility blocker 时可以完成科学设计但标记为尚不可执行；不能用假设值伪装已经具备现实执行条件。

## 4. 冻结与交接

当 Design 将用于真实数据产生或确认性结果判别时，按项目 `research-db` 契约保存 canonical design artifact 与结果前 freeze。首次进入 frozen / execution-ready 前先通过学术语言检查；需要修正的人类科研正文必须在冻结前完成。实际实施由 `study` 记录，任何实际偏离必须作为真实 execution / amendment 保存，而不是回写原 Design。

完成标准：研究对象、估计目标、独立单位、comparison、measurement、主要 bias protection、precision 与 decision boundary 足以判断该研究能否回答当前 scientific target，并明确是可直接实施还是仍有 blocker。
