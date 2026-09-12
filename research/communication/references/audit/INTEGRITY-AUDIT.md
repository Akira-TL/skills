# 科研稿件完整性审计

本文件用于检查已经形成的论文 / 综述稿是否忠实于 canonical evidence。它不负责重新创造科学结论，也不声称自动证明论文“完全正确”。完整性审计分为**初稿审计**与**最终审计**两次，分别位于 reviewer-style review 之前和最终定稿之前。

## 1. 两次审计的时点

### 初稿审计

在主要正文、图表、引用已经形成之后，正式进入 reviewer-style 自审 / 外部审稿模拟之前执行。目的不是追求零措辞问题，而是尽早发现：

- citation 身份错误；
- citation 实际不支持正文 Claim；
- 数字、统计量或图表与 canonical output 不一致；
- 标题 / 摘要 / 结论比正文 evidence boundary 更强；
- 重要 limitation、negative / null result 或 contradiction 被叙事隐藏；
- novelty / priority 声明没有可靠 search basis；
- Methods 与真实执行不一致。

### 最终审计

完成一轮或多轮 revision 后、形成最终交付稿之前执行。除了重复上述核验，还要特别检查 revision 是否引入新的数字错误、citation drift、scope 扩张、Claim 强度升级或 limitation 消失。

两次审计都基于明确的 draft 版本与 source commit；不要用会话记忆代替实际文件。

## 2. Claim—source 核验

Citation 的 reference identity、Claim–source support 与 citation style 统一按 [`CITATION-AUDIT.md`](CITATION-AUDIT.md) 分层检查；本节重点负责 integrity 层的高风险 Claim 覆盖。先从当前稿件提取需要实质证据支持的 Claim，至少优先覆盖：

- Title / Abstract / Conclusion 中的 headline Claim；
- 所有定量 Claim：样本量、比例、effect estimate、confidence interval、`P` 值、threshold、性能数值等；
- causal / mechanistic Claim；
- Methods-critical Claim：随机化、盲法、独立实验单位、模型、排除规则、数据库来源等；
- 已知存在冲突文献或 reviewer 争议的 Claim；
- `first`、`only`、`no previous study` 等 novelty / priority Claim。

对每个被审计 Claim 回答：

1. 它引用或依赖哪个 canonical source？
2. source 中的具体 Observation / result / passage 在哪里？
3. 数字、population、timeframe、method 与正文是否一致？
4. source 真正支持的是 direct support、indirect support、qualification 还是只“主题相关”？
5. 当前正文是否比 source 的 scope、causal level 或 certainty 更强？

citation 存在、DOI 正确，只能证明文献身份，不证明该文献支持当前句子。最终稿还必须做 in-text citation ↔ reference-list 双向核对，并确认 revision 没有改变 citation 的语法作用范围、编号或 Claim attribution。

初稿审计至少完整覆盖所有上述高风险 Claim，并抽查其余实质 Claim；最终审计应尽量覆盖当前稿件中已登记 / 已识别的全部实质 Claim。这里的“全部”只指当前审计识别出的 Claim 集合；模型语义提取不能机械证明自己没有漏掉未识别 Claim，因此最终报告不得宣称“全文所有语义 Claim 已被确定性穷尽”。

## 3. 无法核验时 fail closed

遇到以下情况时明确记录 `unresolved / unverifiable`，不能补造 PASS：

- source 全文当前不可访问；
- 引用只指向 review，但关键数字需要 primary study；
- 论文或补充材料没有报告所需细节；
- 文稿 Claim 找不到对应 canonical result；
- 同一 citation 只能支持 Claim 的一部分；
- novelty 声明没有与当前 search scope / last searched time 对齐。

如果无法核验的内容会改变主结论、Methods 可重复性或主要 reviewer 判断，修正或降级 Claim 后才能继续 finalization。

## 4. 数字、统计与图表表面

对稿件中的关键 quantitative surface 逐项回到 canonical analysis output，至少检查：

- `n` 与 independent unit；
- estimate / effect size；
- uncertainty；
- `P` value / adjusted `P` / multiplicity；
- units、denominator 与百分比；
- table、figure、正文三者是否一致；
- exploratory / confirmatory / post hoc 标签；
- negative / null result 有没有被修订时删除或改写成正向叙事。

文字中“约”“大约”“显著”“明显”等表述不能掩盖原始数值或改变实际精度。

## 5. Reviewer-style 风险审查

完成事实与证据完整性检查后，再以目标期刊 / 学位 / 报告的真实评价标准进行 adversarial review。通用审查轴至少包括：

- technical soundness / validity；
- contribution / originality 是否被现有 evidence 支持；
- evaluation 是否覆盖关键 baseline、control、sensitivity 和 failure mode；
- Methods 与复现信息是否充分；
- Claim 与证据是否匹配；
- readability：跨本小领域的目标读者是否能理解基本背景、做了什么、结果意味着什么。

scientific importance、broader readership、interdisciplinary reach 等只在目标 venue 确实把它们作为评价标准时提高权重；不能把某一家期刊的编辑偏好升级为 Akira 的普遍科研门禁。

若 reviewer-style 审查发现真正需要新增实验、数据或 Analysis，不在 Communication 里伪造完成：返回 `study` / `data` / `analysis` / `literature` 等正确工作流，形成新的 canonical evidence 后再修订稿件。

## 6. 最终 revision drift 审查

最终审计必须比较修订前后的真实稿件，而不是只看 response letter。重点找：

- numerical drift：数字、单位、sample size、effect 或统计量被无依据改变；
- claim-strength drift：`associated with` 被写成 `causes`、`consistent with` 被写成 `demonstrates mechanism` 等；
- scope drift：population / geography / timeframe / system 被扩大；
- limitation drift：原有 caveat、negative result、null result 或 uncertainty 在修订中消失；
- citation drift：新增 citation 不支持新增句子，或删除 citation 后 Claim 失去依据；
- novelty drift：从 search-bounded wording 漂移成绝对“首次 / 唯一”。

只要 drift 会实质改变 evidence boundary，就必须恢复、提供新的 canonical evidence，或由用户明确决定接受有依据的改写；不能把 reviewer response 的说服性文字当成科学授权。

## 7. 审计结论的边界

Integrity audit 的 PASS 只表示：**在当前明确检查范围内，没有留下已发现且未处理的高风险不一致。** 它不证明：

- 原始实验一定真实执行；
- raw data 一定无误；
- 模型提取到了每一个语义 Claim；
- 未抽查部分绝对没有问题；
- 论文必然被期刊接受。

因此最终交付时可以报告“已完成哪些检查、还有哪些 unresolved 项”，不能把审计包装成科研真实性证书。
