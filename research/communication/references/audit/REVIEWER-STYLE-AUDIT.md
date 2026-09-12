# Reviewer-style 多视角审查协议

本文件用于投稿前、答辩前或重大修订前，希望从多个审稿视角检查同一稿件时。目标是增加**问题发现的独立性与覆盖面**，而不是制造“有多个真实 reviewer 已经认可”的假象。

单次 reviewer-style 风险审查仍遵守 [`INTEGRITY-AUDIT.md`](INTEGRITY-AUDIT.md) 的内部效度、外部效度、科学贡献和 evidence boundary。只有确实需要多个不同审查视角时才加载本协议。

## 1. 先固定共同 Review Packet

多视角审查开始前，先固定所有视角共同看到的输入版本：

```text
manuscript / review source version
pre-communication source commit
Figures / Tables / Supplement
可核验的 section / figure / table locator
目标 venue / degree / report 的真实评价标准
当前缺失文件与 assessment boundary
```

共同 packet 不应预先包含：

- 第一个审查视角已经发现的 concern；
- 主 Agent 事先整理好的“最可能问题列表”；
- 预期 consensus；
- 另一份 reviewer report；
- 为了让各视角“有差异”而设计的答案方向。

否则后续审查会被前序 concern 锚定，不能再声称具有独立问题发现价值。

## 2. 审查视角在开始前定义，不在看到结果后补造

如果需要不同 emphasis，可以在审查前定义，例如：

- Design / internal validity；
- statistics / computational rigor；
- domain mechanism / biological or physical plausibility；
- external validity / generalizability；
- literature / novelty / positioning；
- reproducibility / data / code / reporting；
- target-reader readability。

这些是**审查重点（review lens）**，不是虚构的人物身份、机构、资历或真实同行意见。不得写成“某顶刊资深 reviewer 认为……”之类未经事实支持的角色扮演。

所有 lens 仍必须检查会推翻 central Claim 的明显 validity failure；不能因为某一轮被指定“写作视角”，就故意忽略一个已经看见的致命科学问题。

## 3. 真正的独立审查必须有上下文隔离

若运行环境确实支持相互隔离的 Agent / context：

1. 每个审查上下文只接收共同 Review Packet、共同评价标准和自己的 emphasis；
2. 不读取其他审查报告或 concern ledger；
3. 独立识别 central Claim、decisive evidence、major limitation 与 concern；
4. 每个 concern 给出 evidence pointer、severity rationale 和 resolution test；
5. 当前视角报告完成后冻结，不因后续报告相似或不同而回头修改。

只有满足这类隔离条件，才可以描述为“独立 reviewer-style passes”或“相互隔离的多视角审查”。

如果实际是在同一上下文里顺序完成多个视角，必须称为：

- `multi-lens review`；
- `多视角自审`；
- `同一上下文下的多轮 reviewer-style audit`。

不能声称“互盲”“独立 reviewer”或把多个同源判断当作独立重复证据。

## 4. Concern 必须可定位、可解释、可验收

每一个实质 concern 至少包含：

```text
concern
severity / blocking status（若适用）
为什么影响当前 Claim / validity / usability
evidence pointer / manuscript locator
当前 evidence status
resolution test
```

优先使用稳定的 section / Figure / Table / Supplement locator；没有真实 page / line number 时不要发明。

`resolution test` 回答“什么改变会使这个 concern 真正闭合”，例如：

- 增加能隔离目标效应的 control；
- 使用正确的 interaction contrast；
- 补充 sensitivity / external validation；
- 把 causal Claim 降级为 association；
- 明确 population / condition boundary；
- 提供缺失的 method / code / data provenance。

不能用“需要进一步讨论”“建议加强论证”这类无法验收的句子冒充 major concern。

## 5. 不设 concern 数量配额

每个视角可以：

- 找到多个 major concern；
- 只找到 minor issues；
- 没有发现新的 grounded concern。

不要为了让 reviewer report 看起来“像真的”而强制每个视角凑 3 个 major + 5 个 minor，也不要为了制造 reviewer 差异故意把同一问题改名。

没有依据的问题宁可不写。材料不足时用 `not assessable from supplied material`，不能把“没看到”自动推断为“作者没做”。

## 6. 先冻结个体报告，再做综合

只有所有计划的审查 pass 完成并冻结后，才在单独的 synthesis 步骤比较：

- 哪些 concern 在多个独立 pass 中分别出现；
- 哪些是单一视角发现但科学上仍然关键；
- 哪些只是 emphasis 不同；
- 哪些 concern 其实指向同一个底层 validity problem；
- 哪些判断冲突，需要回到 evidence 决定，而不是投票。

不能为了提高“共识度”在 synthesis 后反向改写个体报告，也不能为了展示“多样性”删除重复 concern。

## 7. Consensus 不等于科学真值

即使多个独立审查 pass 都指出同一问题，也只能说明该问题具有较高的**审查显著性/可发现性**，不能自动证明 concern 的科学判断正确。仍需回到 manuscript、canonical evidence 和适用方法学核验。

反过来，一个只有单一视角发现的严重 validity failure 也不能因为“没有共识”就被平均掉。

因此综合时不要使用简单 reviewer vote 或平均分决定：

- scientific validity；
- acceptance / rejection；
- 是否需要新实验；
- Claim 是否成立。

## 8. 审查与修订分开

Reviewer-style audit 先形成 concern 与 resolution test；是否接受、如何修订再进入 revision planning。不要让审查视角一边评估一边为了方便作者而弱化 concern。

如果 concern 要求新的 Study / Data / Analysis / Literature evidence，返回正确科研流程；Communication 不能通过更流畅的 response prose 伪造 closure。

## 9. 最终报告的诚实表述

对外汇报多视角审查时应明确：

- 用了几个 review pass / lens；
- 是否真的使用相互隔离上下文；
- 共同 assessment boundary 是什么；
- 哪些 concern 是 post-hoc synthesis 后识别为重叠；
- 哪些关键问题仍 unresolved / not assessable。

禁止把 Agent reviewer-style audit 包装成真实期刊同行评审、真实专家咨询或外部独立验证。

## 10. 完成条件

若声称完成多视角 reviewer-style audit，至少满足：

1. 共同 Review Packet 与稿件版本固定；
2. review lens 在开始前定义；
3. 每个 concern 有真实 evidence pointer 与 resolution test；
4. 不为凑数制造 concern；
5. 若声称独立/互盲，确实有上下文隔离；否则明确称 multi-lens；
6. 个体报告在 synthesis 前冻结；
7. consensus / disagreement 只在事后综合，不反向污染个体审查；
8. fatal / blocking validity issue 不因平均分、投票或其他维度优点而被抵消；
9. 审查发现的新科研工作返回正确 canonical workflow。

这一协议提高的是 reviewer-style 自审的结构化程度，不意味着稿件已经接受真实外部同行评议。
