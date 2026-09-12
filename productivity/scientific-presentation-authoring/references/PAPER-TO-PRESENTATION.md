# 论文 / 文献汇报工作流

本参考用于把一篇论文、预印本、系统综述或已经完成的结构化阅读笔记转成科研汇报。它补充 `scientific-presentation-authoring` 的通用页面规则，不改变其中“结果页标题描述分析内容、正文陈述可直接支持的结果、解释留给讨论/总结页”的证据边界。

目标不是把论文 section 顺序压缩成幻灯片，而是恢复论文的**科学论证链**，再决定哪些证据值得进入汇报。

## 1. 先恢复论文的 scientific spine

开始分页前，至少回答：

```text
研究为什么值得做？
当前知识缺口 / 技术瓶颈是什么？
作者真正回答的 Research Question 是什么？
采用了什么 Study / Dataset / method / comparison？
哪些 Figure / Table 构成主要证据？
哪些 control / robustness / validation 让主要结论可信？
证据实际支持到什么范围？
哪些 limitation / alternative explanation 仍然存在？
```

如果输入来自 Akira Literature Research，优先消费已经完成的 Reconstruction / Critical Audit 与人类阅读 sidecar，不重新凭摘要猜论文逻辑；关键结果仍应回到原论文 Figure / Table / Supplement locator 核对。

不要把作者 Discussion 中的解释直接当成数据结果，也不要为了汇报更有故事性而抹去负结果、关键 boundary 或 contradictory evidence。

## 2. 先分类论文，再选叙事顺序

论文类型只决定汇报顺序，不改变 evidence boundary。

### 2.1 Discovery / mechanism paper

推荐主线：

```text
问题与 gap
→ experimental / observational design
→ 第一条决定性 Observation
→ 后续判别性 Experiment
→ control / robustness
→ mechanism-compatible evidence
→ conclusion boundary / unresolved alternative
```

不能因为作者提出机制模型，就把所有关联结果都写成机制已经建立。

### 2.2 Methods / algorithm paper

推荐主线：

```text
现有方法的具体瓶颈
→ 新方法解决什么 target problem
→ method / model architecture 到听众需要理解的粒度
→ benchmark / baseline comparison
→ ablation / sensitivity / calibration
→ external validation / transferability
→ failure mode / computational or data dependency
```

不要用模型结构页替代性能证据，也不要只展示最有利 benchmark 而遗漏会改变方法评价的重要失败场景。

### 2.3 Resource / dataset / atlas / benchmark paper

推荐主线：

```text
为什么需要该 resource
→ sample / source / collection / construction
→ coverage / QC / annotation
→ resource 的核心组成
→ validation / representative use case
→ access / reuse route
→ coverage boundary / bias / missing population or modality
```

资源型论文的价值不能只用“规模最大”表达；应说明 coverage、质量、可复用性和真正支持的研究任务。

### 2.4 Clinical / population / intervention paper

推荐主线：

```text
clinical / population question
→ population 与 study design
→ exposure / intervention / comparator
→ primary outcome / estimand
→ main result + uncertainty
→ safety / secondary outcome / subgroup（适用时）
→ bias / confounding / missingness / generalizability
→ 最窄可辩护结论
```

观察性研究的结果页不得通过汇报措辞升级成 intervention causality。

### 2.5 Materials / chemistry / physics / engineering paper

推荐主线：

```text
design problem / target property
→ material / process / structure design
→ characterization / experimental conditions
→ central performance evidence
→ matched control / benchmark
→ stability / repeatability / sensitivity
→ mechanism evidence（若有）
→ operating boundary / scale-up or transfer limit
```

性能数字必须保留测试条件和 comparator；跨论文 benchmark 不同条件时不能直接做无条件优劣排名。

### 2.6 Review / perspective / evidence synthesis

推荐主线：

```text
Review Question / Scope
→ evidence landscape / taxonomy
→ areas of agreement
→ conflicting evidence / competing explanation
→ method or evidence-quality boundary
→ unresolved gap
→ future direction / actionable implication
```

正式 Systematic Review / Meta-analysis 若已有 protocol、screening、risk-of-bias 与 synthesis 结果，应把这些方法学要素作为证据可靠性的一部分；不能只展示最终 pooled estimate。

## 3. Figure 按证据作用选，不按论文编号顺序搬运

优先选择真正承担论证作用的视觉证据：

1. Study / workflow / experimental design；
2. central evidence；
3. control / robustness / validation；
4. mechanism / synthesis / model；
5. boundary / failure / representative exception。

不要求 Figure 1 → Figure 2 → Figure 3 顺序完整覆盖。一个论文 Figure 如果 panel 很密，可以只使用当前页面需要的 panel，但必须：

- 保留原始 data visual，不修改数据含义；
- 保留必要 axis、unit、legend、panel label、scale bar、statistical annotation；
- 页面或讲稿能定位回原 Figure / Table / Supplement；
- crop 后仍能判断比较对象和统计含义；
- 不把不同实验条件的 panel 拼接成看似同一 comparison。

如果裁剪会丢失科学信息，拆页或使用完整 Figure，不为了版式强行裁掉。

## 4. 每页只承担一个 evidence job

论文汇报的结果页优先区分以下角色：

- **Design**：这一实验为什么能回答当前问题；
- **Observation**：图表直接显示了什么；
- **Validation**：为什么该结果不是明显 artifact / overfit / batch effect；
- **Comparison**：相对 control / baseline / prior method 差异是什么；
- **Boundary**：在哪些 population / condition / metric 下结论不成立或尚未检验；
- **Interpretation**：作者如何解释；
- **Critical audit**：我们认为最关键的 inference gap / alternative explanation 是什么。

不要在一张结果页同时塞满实验设计、数字结果、作者机制解释、自己的批判和未来工作。需要时拆成连续两页或把解释放讲稿。

## 5. 页面正文与 speaker notes 分工

页面正文只保留观众必须看到的：

- comparison object；
- key quantitative result；
- effect direction / uncertainty / significance（若正式计算）；
- Figure 中不容易一眼看出的必要 condition；
- source locator。

Speaker notes 可以承担：

- why this experiment；
- Figure 阅读顺序；
- method / metric 的短解释；
- 与上一页/下一页的推理关系；
- 作者解释与我们的 Critical Audit；
- limitation 和可能被问到的 caveat。

不要把 notes 的口语解释全部挤到页面。

## 6. 论文术语在整套 slides 中锁定

论文汇报特别容易在多页中出现 model / Dataset / treatment / metric 的译名和缩写漂移。第一次出现时确定：

```text
canonical Chinese / original English / acronym / unit or notation
```

后续保持同一形式。不得为了中文表达变化随意把同一专业概念换成多个近义名称；领域已有规范译名时优先使用规范表述。

## 7. Critical Audit 不与作者结论混写

文献汇报常常既要“讲清作者说了什么”，又要“讲我们的判断”。必须视觉或语言上明确区分：

- **作者结果 / 作者解释**；
- **我们依据论文证据做出的 Critical Audit**；
- **当前无法判断 / 未报告 / 需要额外证据**。

不能把我们的 alternative explanation 写成作者已经讨论的结论，也不能把作者 Discussion 的 speculative mechanism 写成直接 Observation。

## 8. 最终 QA

论文 / 文献汇报交付前额外检查：

1. slide order 是否围绕论文 argument，而不是机械复现 section 顺序；
2. central Claim 是否有至少一张清楚、可读的决定性 evidence slide；
3. 关键 control / robustness / validation 是否在需要时出现；
4. 负结果、exception 或 limitation 是否被故事化删掉；
5. 每条重要数字是否来自原文或已核验阅读记录；
6. Figure crop 是否保留 axis、unit、legend、panel label、scale bar、统计标记；
7. 页面中的 interpretation 是否超出论文 evidence boundary；
8. 作者解释与我们的 Critical Audit 是否清楚分开；
9. 同一术语、metric、unit 和 abbreviation 是否全套一致；
10. speaker notes 是否承担了应该口头解释而不应堆在页面上的内容；
11. 实际 PPTX 若已生成，必须再检查 text overflow、shape overlap、Figure 可读性和渲染后的页面效果，不能只以文件可打开作为完成标准。

完成标准不是“把所有 Figure 都讲过”，而是听众能沿着最短、完整、诚实的 evidence chain 理解：作者为什么做、做了什么、数据真正显示什么、结论为什么可信，以及仍然不能推出什么。
