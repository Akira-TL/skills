# Evidence Synthesis Contract

`research-db evidence` 输出的是 provenance-preserving evidence packet，不是科研结论。Evidence Synthesis 是 Agent 在读取 packet、原始 artifact 和必要全文上下文后的解释步骤。所有面向用户的科研表述同时遵守 [`ACADEMIC-LANGUAGE.md`](standards/ACADEMIC-LANGUAGE.md)；本文件中的 `supported`、`qualified`、`evidence_families` 等是内部工作流/数据结构标签，不自动属于学界术语，不能在用户科研文本中被包装成新概念。

## 输入

Synthesis 必须接收：

- research question / target claim；
- evidence packet，包括展开后的 evidence units、relations、Paper identities 与 evidence families；
- 必要时回查原始 paper artifact。

不得只根据检索 snippet 生成结论。

## 输出边界

每个结论必须归入以下之一：

- `supported`：已有直接证据支持，但仍需说明适用范围。
- `indirectly_supported`：证据链存在 inference gap，必须说明 gap。
- `qualified`：结果存在限制条件、替代解释或边界条件。
- `contradicted`：存在可信反证或不一致结果。
- `unresolved`：当前证据不足以区分解释。

禁止输出没有对应 evidence unit 的新事实。共享 cohort/sample/dataset 的 Paper 必须按 evidence family 视为相关证据来源，不能按论文篇数当作独立 replication 投票。

## 必须回答

1. 当前问题是什么？
2. 哪些 observation 支撑哪些 claim？
3. 哪些关系只是关联而不是因果？
4. 最大的 alternative explanation 是什么？
5. 当前最大的 unresolved uncertainty 是什么？
6. 什么新增 evidence 最能区分 competing explanations？

## 禁止行为

- 不把多个 indirect evidence 自动升级为 causal evidence。
- 不把作者 claim 当作独立证据。
- 不生成 evidence score 替代科学判断。
- 不隐藏 contradiction、negative result 或 reporting gap。

## 人类可读综合格式（内部模板）

Evidence Synthesis 的人类可读输出应保持下面的信息结构，避免退化为普通文献综述；标题可按用户语言采用规范学术表述，不把内部模板名当作新的学术概念：

```text
Research Question:

Current Evidence State:

Supported:
- claim
- linked evidence units
- scope boundary

Indirectly Supported:
- claim
- inference gap

Qualified:
- limitation
- alternative explanation

Contradicted:
- conflicting evidence

Unresolved:
- question that current evidence cannot distinguish

Most Discriminating Next Evidence:
- observation / experiment / analysis that would reduce uncertainty
```

该报告是 derived synthesis，不替代 `research.sqlite` 中的 Paper、Observation、Claim、Issue 和 Relation canonical records。
