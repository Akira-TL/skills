# 审稿意见与修订流程

本文件用于 reviewer response、major/minor revision、学位评审修改和其他“已有稿件 + 外部意见 + 修订稿”的场景。目标是把每条意见落实到真实 manuscript / analysis / experiment / citation artifact，而不是只写一封听起来合理的回复信。

## 1. 先建立意见—动作—证据对应关系

对每一条 reviewer / editor comment，先保存其原意和上下文，再明确：

- comment / concern 是什么；
- 它要求解决的科学或表达问题是什么；
- 验收标准是什么：什么实际变化才算 fully addressed；
- 需要什么输入；
- 应修改 manuscript 的哪里；
- 是否需要 text、citation、analysis、experiment、figure/table、scope/claim adjustment；
- 完成后用什么 artifact / locator 证明已经做完。

常见处理方向包括：

- 修改正文结构或措辞；
- 补充已有 Methods / Results 细节；
- 增加已核验 citation；
- 运行新的 Analysis；
- 增加真实实验 / 数据；
- 修改 Figure / Table / Supplement；
- 降低 Claim 强度或增加 limitation；
- 部分接受并说明剩余边界；
- 基于证据不同意 reviewer 判断；
- 说明建议超出当前研究设计 / manuscript scope；
- 请求用户提供缺失事实或决定。

“我们已经修改”不是一个可核验动作；必须指向实际改稿、analysis output、figure、citation 或其他 inspectable artifact。

## 2. 修订任务状态必须区分“说完成”和“已核验完成”

对每条意见至少区分以下语义：

- 尚未处理；
- 需要新增文本；
- 需要新增 Analysis；
- 需要新增 Study / Experiment；
- 需要用户确认 / 提供事实；
- 用户或作者声称已经完成，但当前没有可检查 artifact；
- 已找到实际 artifact 并核验完成；
- 当前设计下不可完整实现，需要 limitation / scope response；
- 建议基于证据不同意 reviewer，需要用户确认立场。

一封已经写好的 response letter 不会把任何 `analysis / experiment / figure / manuscript change` 自动升级为“完成”。

例如 reviewer 要求 robustness analysis：只有实际 Analysis 形成 result、稿件相应更新并可定位后，才能说“已完成”；只写“we have performed additional analyses”而没有结果 artifact 时保持未核验。

## 3. 需要新科学工作时退出 Communication

如果 comment 实际要求：

- 新实验 / 新样本 / 新测量；
- 新数据处理；
- 新统计模型或 sensitivity；
- 补查关键文献；
- 重新解释会改变当前 scientific Claim；

则先回到 `study` / `data` / `analysis` / `literature` / `interpretation` 等正确科研流程。新的结果成为 canonical evidence、形成新的 source commit 后，才回 Communication 修改稿件和 response。

不得为了尽快写 rebuttal，在 Communication 中虚构“新增实验”“新增分析”或未真实产生的结果。

## 4. Re-review 使用 evidence-before-persuasion

修订是否真的解决 reviewer concern，不能先被作者 response letter 的说服性叙事锚定。默认顺序：

```text
原 reviewer comment / editor decision
→ 固定验收标准
→ 查看 original manuscript（需要时）
→ 独立检查 revised manuscript / analysis / figure 等真实 artifact
→ 先得出“实际解决到什么程度”的判断
→ 最后再读取 response letter
→ 检查 response letter 是否准确描述真实修改
```

### 4.1 验收标准先固定

在阅读修订稿的辩解文字前，先把 reviewer comment 转成可检查问题。例如：

```text
Reviewer: 需要证明结果不依赖某个阈值。

验收标准：
- 至少包含预先说明的合理替代阈值；
- 相同 Dataset / estimand 下报告 sensitivity；
- 若结论改变，正文必须更新边界。
```

不能看到修订稿后再偷偷降低或提高验收标准。

### 4.2 先看实际证据，再看作者回复

先检查：

- revised text 是否真的改了；
- reviewer 指出的结果 / 方法 / figure 是否真实存在；
- 新 Analysis / Experiment 是否有 canonical artifact；
- 变化是否满足刚才固定的验收标准。

之后才看 response letter。response letter 可以帮助定位修改，也可以提供 rebuttal reasoning，但它不能凭“作者说已经解决”改变 manuscript-side evidence。

如果 reply 指向一个之前遗漏的真实位置，可以据此重新检查；最终依据仍然是稿件 / evidence 本身。

## 5. 对 reviewer 的不同意也必须有证据

并非所有意见都必须接受。可以不同意的典型情况包括：

- reviewer 把已有结果读错；
- 请求超出当前 Research Question / Design；
- reviewer 要求的方法会引入更严重偏倚；
- 当前 canonical evidence 已经直接反驳 concern；
- 新实验成本与科学增益极不匹配，而且当前结论可以通过降级范围诚实保留。

不同意时：

1. 先复述 concern，避免 strawman；
2. 给出 manuscript / data / literature 的具体 evidence；
3. 说明为什么当前处理更合理；
4. 若 reviewer 的误解暴露了表达问题，即使科学结论不变，也应考虑澄清稿件；
5. 对高风险 disagreement，在最终 response 前取得用户明确确认。

不要用“reviewer did not understand”作为回复理由。

## 6. Reviewer 之间冲突时不静默调和

若 Reviewer A 与 Reviewer B 要求相反修改，例如一个要求扩大 Discussion、另一个要求大幅压缩，或者对同一 scientific Claim 要求相反强度：

- 明确标记冲突；
- 分别记录两条意见的科学依据和 target venue / editor context；
- 判断是否存在同时满足两者的更高层解决方案；
- 若仍然冲突，把可选方案和后果交给用户 / corresponding author 决定；
- 不允许 Agent 在没有说明的情况下选择其中一方并让另一条意见“消失”。

## 7. Response letter 的写法

对每条 comment 推荐采用：

```text
Comment
→ Response / scientific position
→ Action actually taken
→ Evidence / manuscript location
```

回复语气专业、简洁、无防御性；感谢不是必须套话，重点是让 editor / reviewer 快速确认：

- 你理解了什么问题；
- 具体做了什么；
- 新 evidence 是什么；
- 哪里可以看到；
- 若没有完全接受，边界和理由是什么。

只有真实完成的修改才能使用 completed tense。仍待用户、analysis 或 experiment 的项目必须保留显式 placeholder / open status。

## 8. 最终修订检查

所有 reviewer comment 处理完成后：

1. 按最初验收标准重新检查每条 concern；
2. 验证 response letter 对“已完成”的每个陈述都能找到实际 artifact；
3. 检查 manuscript、Supplement、Figure legend 和 response letter 是否彼此一致；
4. 运行 [`INTEGRITY-AUDIT.md`](INTEGRITY-AUDIT.md) 的最终审计，特别检查 Claim strength、数字、scope、limitation 和 citation drift；
5. 若 reviewer revision 导致 canonical scientific state 发生变化，更新 source commit / communication provenance，不能继续声称稿件基于旧 freeze。

最终目标不是“每个 reviewer 都被说服”，而是每条重要 concern 都有一个真实、可核验、科学上诚实的 disposition。
