# 原始研究论文写作流程

本文件只约束**以本项目新产生的 Study / Data / Analysis / Observation / Interpretation 为主要科学贡献**的原始研究论文，以及同类 research thesis / research report。它规定的是写作顺序、材料组织和逻辑审查，不创造新的科研事实。所有主要结论仍必须来自已经稳定的 Analysis / Interpretation 与 canonical evidence；写作阶段只能组织和表达已有科学状态。文献综述不得套用本流程，进入 Communication 后应先按 [`WRITING-ROUTER.md`](WRITING-ROUTER.md) 判定文稿类型。

## 1. 先完整盘点写作材料

正式起草正文前，先把与当前 Research Question、主要结果和结论边界有关的材料完整摊开。材料盘点必须覆盖对当前论文有实质关系的内容，而不是只收集“适合主线”的结果。

至少检查：

- primary / confirmatory result；
- negative、null、与预期相反的结果；
- exploratory result；
- sensitivity / robustness analysis；
- QC、异常和重要数据边界；
- protocol deviation、analysis amendment、post hoc change；
- 支持与限制主要 Claim 的分析；
- alternative explanation；
- limitation 与 unresolved uncertainty；
- 支持、限定、冲突的 literature evidence；
- figure / table 与其 canonical source；
- supplementary result、supplementary method 与复现信息。

**材料必须尽可能完整，论文正文则可以有主次。** 不得因为某项结果不利于预期故事、难以解释或不够“漂亮”而从写作材料视野中消失。

对原始研究论文及同类长篇 research thesis / report，默认维护一个 Communication 阶段的 `MATERIALS.md` 或等价清单。它是从 canonical evidence 派生的写作导航，不是新的科学事实源。每一项重要材料至少标明：

- 来源 artifact / Analysis / Paper；
- 它回答什么；
- 与主要结论的关系；
- 最终去向；
- 若不进入主文，为什么。

合法去向包括：

```text
Main text
Supplement
Appendix
Canonical support only
```

`Canonical support only` 只表示它不进入本次传播正文，不能用来掩盖会改变主要 Claim、limitation 或 evidence boundary 的材料。会改变读者对主要结论判断的重要负结果、冲突证据和局限必须在主文或 Supplement 中以适当形式披露。

## 2. 默认写作顺序：先结论，再结果与讨论，最后反推前言

长篇科研论文默认按下面顺序起草，而不是从 Introduction 顺写到 Conclusion：

```text
完整材料盘点
→ 主要结论
→ Results
→ Discussion
→ 反推 Introduction
→ Methods
→ Abstract / Title
→ Supplement / Appendix
→ 大逻辑与小逻辑审查
```

### 2.1 先写主要结论

先从已稳定的 Interpretation 中写出当前论文最重要的少量结论，明确文章真正要解决什么。每个主要结论同时注明：

- 结论正文；
- 主要证据；
- 适用范围；
- 关键限制或反证；
- 当前 evidence level。

先写结论的目的，是固定论文核心并反推后续写作；**不是**在 Communication 阶段先想一个漂亮故事，再回头挑数据证明它。

### 2.2 再写 Results

根据主要结论决定 Results 需要呈现哪些结果、以什么顺序呈现。写长 prose 前，先用**小标题 + Figure/Table + 简要内容**搭出 Results 骨架。每个结果小节至少写清：

```text
本节回答什么问题
Figure / Table 是什么
关键 Observation 是什么
本节最窄结论是什么
为什么这个结果自然引出下一节
```

小标题应表达该小节解决的科学问题或得到的主要信息，而不是机械写成“Figure 2 结果”“实验三结果”。标题本身仍受 evidence boundary 约束。

Results 不应是 Figure A、Figure B、Figure C 的流水账。理想的推进关系是：

```text
结果 A 建立现象
→ A 暴露新的 uncertainty / 无法区分的解释
→ 因此需要结果 B
→ B 缩小解释空间
→ 因此进一步测试 C
```

如果交换两个相邻结果小节的位置后论文几乎没有任何逻辑损失，应重新检查它们是否只是并列罗列，而没有形成真正的科学推进。

### 2.3 然后写 Discussion

Discussion 围绕已经写出的 Results 和主要结论展开，不另起一套故事。至少系统处理：

- 本研究最重要的发现；
- 与已有研究一致的部分；
- 与已有研究不同或冲突的部分；
- 差异可能来自哪些 population、design、measurement、analysis 或 context；
- 能否归纳出更一般的规律；
- 当前证据能支持到 descriptive、association、causal 还是 mechanistic 层级；
- plausible mechanism 与 alternative explanation；
- limitation、scope boundary 与 unresolved question；
- 研究结果的科学意义。

应主动比较支持、限定和冲突文献，不得只挑与本研究一致的引用。若写作时发现 literature evidence 不完整，返回 `literature` 补足后再继续。

**深入讨论机制是需要主动尝试的科研写作动作，但不能强迫证据升级。** 若数据只与某机制一致，应写成 plausible mechanism / hypothesis；只有现有证据真的达到 mechanistic level 时，才能写成机制结论。

### 2.4 最后反推 Introduction

Introduction 不从大背景漫无边际地顺写，而是从已经稳定的主要结论、Results 和 Discussion 反推读者在进入论文前必须建立什么问题。

默认逻辑：

```text
研究背景与核心问题
→ 已有研究已经知道什么
→ 仍然不知道什么 / 现有研究有什么不足或矛盾
→ 为什么这个 uncertainty 值得解决
→ 本研究针对什么问题、采用什么总体策略
```

Introduction 中提出的每一个主要 research gap、研究目标或 contribution，都必须在后续 Results / Discussion 中有对应闭环。反过来，论文的主要结论也不能在 Introduction 完全没有铺垫的情况下突然出现。

“创新点”只能从已经建立的科学贡献中提炼，不能在写作阶段为了叙事需要新造一个贡献。

## 3. Results / Discussion 的六项组织检查

起草和修订 Results / Discussion 时逐项检查：

1. **结构清晰**：按科学问题、实验现象和研究解释拆成小节，小节之间有明确推进关系。
2. **主次分明**：核心结果进入主文；重要但次级内容进入 Supplement / Appendix；不相关内容不占据主要叙事。
3. **图表结合**：Figure / Table 负责呈现数据，正文负责指出关键模式、必要数值、科学含义和下一步逻辑，不逐项朗读图表中的所有数字。
4. **文献对比**：比较一致、差异与冲突证据，并讨论造成差异的合理原因。
5. **深入分析**：不满足于表面现象；在证据允许的范围内寻找规律、解释、机制与替代解释。
6. **紧扣核心**：每个主要小节都能解释自己对论文主要结论的作用。

## 4. 材料完整与正文聚焦同时成立

“主次分明”不等于“删除不顺眼的数据”。材料层必须完整，传播层才决定主文和 Supplement 的分配。

对任何重要结果，最终都应该能回答：

> 这项材料在本次论文里去了哪里？

若答案只是“没有写，因为不适合故事”，则写作尚未完成。

## 5. Figure / Table 优先搭骨架

长篇论文在写完整 Results prose 前，先按主要结论排列核心 Figure / Table。推荐对每个主要图表记录：

| 项目 | 内容 |
| --- | --- |
| Scientific question | 这张图回答什么 |
| Key observation | 数据直接显示什么 |
| Supported claim | 它最多支持到什么 |
| Story role | 建立现象 / 排除解释 / 机制支持 / 稳健性 / 泛化等 |
| Next step | 为什么下一张图自然出现 |

Figure 顺序必须有科学理由，而不是按分析完成时间、文件名或视觉效果排序。

## 6. Introduction—Results—Discussion—Conclusion 首尾闭环

原始研究论文及同类长篇 research thesis / report 在成稿前建立一个简短对应表，至少检查：

| Introduction 中的问题 / 不足 | 本研究如何处理 | Results | Discussion | 主要结论 |
| --- | --- | --- | --- | --- |
| Gap / Question 1 | Design / Analysis | Result section | Discussion section | Conclusion |

如果 Introduction 提出了论文实际上没有回答的问题，缩小 Introduction；如果 Results / Discussion 中出现一个重要科学主张但 Introduction 没有建立其来源，补足必要铺垫或重新评估该主张是否属于本论文。

## 7. 大逻辑审查

全文完成后先审整体论证，再审语法和措辞。至少回答：

- 论文真正的核心问题是什么？
- 主要结论是否清楚且数量受控？
- 所有主要章节是否围绕这个核心？
- Introduction 提出的问题是否被 Results 回答？
- Results 是否层层递进，而不是并列堆积？
- Discussion 是否解释关键 Results，并回到 Introduction 的 gap？
- Conclusion 是否确实由前文推出？
- 是否存在篇幅很大但与核心结论关系很弱的支线？如果有，它应该进入 Supplement 还是另一个研究问题？
- 是否有会改变主要结论的材料被遗漏？

## 8. 小逻辑审查

再逐节、逐段检查局部推理：

- 每一节是否只有清楚的中心问题？
- 每一段是否主要承担一个论点或推理任务？
- 当前句与上一句是补充、转折、因果、解释、举例、让步还是总结？
- 这个关系是否真的成立？
- 是否存在跳跃推断？
- 是否把相关性写成因果？
- 同一概念是否中途改变定义或术语？
- 当前结论的证据是否已经在前文出现？
- 下一段为什么应该出现在这里？

连接词和句式只负责**表达已经存在的逻辑关系**。具体受控表达与常见误用见 [`WRITING-EXPRESSION.md`](WRITING-EXPRESSION.md)。

## 9. Methods、Abstract、Title 与 Supplement

完成 Results / Discussion / Introduction 后再补齐 Methods，确保它与真实执行完全一致，并与 [`CONTRACT.md`](CONTRACT.md) 的 reproducibility 规则一致。

Abstract 和 Title 最后写，因为它们必须压缩已经完成的整篇论文，而不是预先规定论文要得到什么。Title、Abstract、Conclusion 的 Claim 强度不得高于正文。

Supplement / Appendix 在正文主线稳定后统一整理，承接重要但不宜打断主叙事的材料；Supplement 不是隐藏不利证据的地方，而是完整报告科研材料的一部分。
