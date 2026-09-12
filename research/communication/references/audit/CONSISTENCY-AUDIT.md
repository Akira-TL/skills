# Manuscript Consistency Audit

本审计针对已经存在的完整 manuscript / thesis chapter / long-form report，检查多轮写作和修订后产生的**全文内部漂移**。它与 [`INTEGRITY-AUDIT.md`](INTEGRITY-AUDIT.md) 不同：Integrity 重点检查 Claim 是否忠于 canonical evidence；本审计重点检查同一份传播产物内部，术语、数字、单位、统计、cross-reference 与 summary 是否彼此一致。

它也不同于 [`../WRITING-EXPRESSION.md`](../WRITING-EXPRESSION.md) 中的局部术语规则：后者用于写作时预防概念漂移，本审计用于完整稿件完成后的 retrospective sweep。

## 1. 适用时点

以下场景应运行：

- 完整长篇 draft 已形成，准备进入 reviewer-style self-review；
- manuscript 经历多轮 revision / 多人编辑；
- Abstract、Results、Discussion、Conclusion 或 Supplement 被分阶段改写；
- 最终投稿前；
- reviewer comment 导致多处联动修改后。

单段润色不需要为了形式完整运行全文审计；但如果局部修改改变了一个在全文重复出现的数字、术语、metric、sample count、Figure/Table 编号或 Claim，必须检查其全部出现位置。

## 2. 先固定 canonical terminology，再找 drift

同一科学对象原则上使用一个稳定名称。完整稿件至少检查：

- treatment / control / cohort / sample / participant / specimen；
- method / model / pipeline / module；
- Dataset / benchmark / assay / material / reagent；
- gene / protein / species / cell line 等领域规范名称；
- metric、statistical symbol、unit 与 mathematical notation；
- acronym / abbreviation 的首次定义和后续使用；
- 本研究自定义但已经用户确认的术语。

不要因为“避免重复”把专业名词换成近义词。若同一概念存在多个变体，先判断它们是否真的是同一对象；不能仅凭字符串相似自动替换。若一个词实际上承担两个不同概念，优先消除歧义，而不是把两个概念统一成一个名字。

对 manuscript 中真正反复出现且容易漂移的术语，可在 working notes 中维护轻量 ledger：

```text
canonical term | first-use form | existing variants | decision / rationale
```

该 ledger 是写作辅助，不创建第二套 scientific state；概念定义仍由 canonical Research / Data / Analysis / Literature 来源决定。

## 3. 数字必须跨全文自洽

所有在多个位置重复出现的重要数字必须从 canonical output 或正式 artifact 重新核对，不能依赖记忆。

重点检查：

- `n`、sample / participant / study / feature / comparison 数量；
- group size、time point、batch、replicate 数量；
- effect estimate、CI / interval、P / FDR、correlation、accuracy 等；
- percent、fold change、range、threshold；
- Figure / Table / Supplement 中与正文重复的值；
- Abstract、Results、Discussion、Conclusion 中重复出现的 headline number。

### 3.1 Headline count 必须能从 Methods / Dataset provenance 推导

若稿件写“共有 640 个样本”，Methods / Study / Data 中必须存在可解释这个数量的真实 provenance；不能出现正文计数与设计因子相乘后明显不一致，而不说明额外 measurement、derived record、dropout 或 exclusion 的情况。

### 3.2 同一 metric 使用一致的数值精度

同一个 estimate 在 Abstract 写 `8.26`、Results 写 `8.258`、Table 写 `8.3` 时，应先判断目标 venue / measurement precision，再采用一个合理且稳定的精度。不能为了排版随意截断或增加小数位。

数值精度一致不等于所有 metric 必须使用相同小数位；不同量的 measurement resolution 可以不同。

### 3.3 同一个值不应在不同位置代表不同对象而不说明

两个不同 quantity 恰好都有相同整数或比例时，必须靠清楚的 label 区分，避免读者误以为它们是同一计数。

## 4. 单位、符号和统计术语保持科学一致

同一 quantity 默认使用同一单位体系，除非目标 venue 或学科规范明确要求转换。若确实需要同时出现不同单位，conversion 必须准确且语境清楚。

重点检查：

- `mm` / `cm`、`mg` / `µg` 等同量换算；
- concentration、time、temperature、pressure 等量纲；
- `%`、fraction、ratio、fold-change 的表述；
- mean ± SD / SE 的定义；
- confidence interval、prediction interval、credible interval 等不能混用；
- statistical abbreviation 和 symbol 在 text / table / legend 中一致；
- 同一 threshold 的方向和比较运算符一致。

发现单位不一致时，先确认 quantity identity 和 canonical output，再修改传播文字；不得通过文字统一掩盖上游数据本身的真实差异。

## 5. Manuscript summary 必须与正文和显示内容一致

逐项核验：

```text
Title / Abstract
↕
Results prose
↕
Figure / Table / Supplement
↕
Discussion / Conclusion
```

特别检查：

- Abstract 的主要结果在 Results 中真实存在；
- Conclusion 没有遗漏会改变中心结论的重要 boundary；
- Discussion 没有把一个 Results 中只成立于 subgroup / condition 的结果扩展到总体；
- “最高 / 最佳 / consistently / all / always”等 superlative 与实际表格全部列一致；
- Results 中多个因素共同贡献时，Abstract / Conclusion 不应事后只归因其中一个；
- 负结果、non-significant result 或 exception 没有在 summary 中被删除到改变科学含义；
- Figure legend 与正文对 panel、group、n、统计检验的描述一致。

同时检查**underclaiming**：若 canonical result 明确建立了一个更强但仍可辩护的结论，不应因多轮修订造成 Abstract / Conclusion 只剩模糊或错误的弱化总结。

## 6. Cross-reference 与结构引用不能漂移

多轮修改后检查：

- Figure / Table / Supplement 编号；
- section / subsection 引用；
- appendix / supplementary item locator；
- equation / algorithm / protocol cross-reference；
- “above / below / previous section / following figure” 等相对定位。

删除、拆分、合并或重编号任一 artifact 后，全文搜索旧 locator。最终排版后若 response letter / cover letter 依赖 page / line locator，再按对应 package workflow 重新核验。

## 7. Redundancy 与局部插入造成的重复

revision 新增一句或一段后，重新阅读相邻段落，检查它是否只是换词重复已有内容。Display 已经完整呈现的数字，不需要在 prose 中逐项抄一遍；正文保留读者需要理解的 contrast、pattern、boundary 和 interpretation。

删除重复内容时不能顺手删掉必要 limitation、negative result、source locator 或条件限定。

## 8. 审计顺序

推荐按以下顺序执行，因为前一步修改往往会使后一步重新失效：

1. **数字 / statistical result / claim-versus-own-data**；
2. **单位 / symbol / interval terminology**；
3. **terminology / acronym / naming**；
4. **Abstract–Results–Discussion–Conclusion summary consistency**；
5. **Figure / Table / Supplement / section cross-reference**；
6. **redundancy 与 local wording**；
7. 若进行了任何实质修改，再运行适用的 Citation、Integrity、revision-package / submission-package 检查。

机械搜索、脚本计数和 diff 可以用来发现候选 drift，但不能自动决定两个术语是否同义、两个数字是否属于同一 quantity，或一个 Claim 是否应该加强 / 降级。最终科学判断仍回到 canonical source。

## 9. 完成条件

一致性审计通过至少意味着：

- 同一科学对象没有未解释的名称漂移；
- acronym 首次定义与后续使用一致；
- 重复出现的重要数字、统计量和 precision 一致；
- 同一 quantity 的单位与符号无未解释冲突；
- headline count 可回到真实 Study / Dataset / Analysis provenance；
- Abstract、Results、Discussion、Conclusion 与 Figure/Table 对同一结果的范围和强度一致；
- superlative、all/always/consistently 等强表述经稿件自身数据核验；
- cross-reference 全部指向真实且当前存在的对象；
- 多轮 revision 没有留下明显重复、孤立句或旧 locator。

本审计只能证明当前传播文本内部没有发现这些一致性问题，不能替代上游 scientific validity、Citation Audit 或 Integrity Audit。
