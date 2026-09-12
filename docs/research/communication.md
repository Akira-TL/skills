# communication

`communication` 把已经稳定的 scientific state 转成论文、综述、报告、摘要、图表、补充材料、答辩或 reviewer response。

传播产物必须基于一个明确的 pre-communication source commit，并从 canonical Research / Design / Study / Data / Analysis / Interpretation 与已核验 Literature evidence 取事实。Title、Abstract、Discussion、Conclusion 和 Figure legend 都不能为了叙事冲击力升级 evidence boundary。传播文件是派生输出，不成为新的科研事实源。

进入长篇写作后，第一步不是直接起草正文，而是先判定整篇传播产物到底是在**报告已经完成的研究、综合既有文献，还是提出未来研究计划**。若主要贡献来自本项目新产生的 Study / Data / Analysis / Observation，则按原始研究论文流程；若主要贡献来自既有文献的组织、比较、批判和综合，则按普通叙述性综述流程；若核心任务是说明未来准备回答什么、怎样回答、如何判断成败以及为什么可行，则按 Proposal 流程。原始研究论文中的 literature review 不会因此变成综述；普通综述有表格、概念图或 bibliometric summary 也不会因此自动变成原始研究论文；Proposal 中有 preliminary data 也不会因此自动变成 Results manuscript。

原始研究论文及同类 research thesis / report 先完整盘点写作材料，再采用“主要结论 → Results → Discussion → 反推 Introduction → Methods → Abstract / Title → Supplement / Appendix”的起草顺序，而不是从前言一路顺写。写 Results prose 前先用小标题、Figure / Table、关键 Observation、本节最窄结论和下一步关系搭骨架；Introduction 中提出的主要问题、研究不足和 contribution 必须在后续 Results / Discussion 中形成闭环。材料要求尽可能完整：主要结果、负结果、非显著结果、探索性结果、敏感性分析、QC、deviation、替代解释、局限、支持与冲突文献等都先进入材料盘点，再决定进入 Main text、Supplement、Appendix 或只保留为 canonical support。Main text 只保留建立主要发现所必需的最短充分证据链以及会改变结论的关键边界；不改变中心解释的 secondary metric、额外 robustness 和 provenance 细节可以进入 Supplement / Methods，但不能用这一分配隐藏 conclusion-changing evidence。

普通叙述性综述不套用 Results / Discussion 流程。它先固定 Review Question / Scope，再盘点基础工作、代表性研究、近期研究、不同理论/方法路线、支持与冲突 evidence、边界条件和 unresolved uncertainty；随后按主题或问题建立分类框架，做跨论文比较与综合，形成理论/概念框架，再从综合结果推出真实 gap、future direction 与综述自己的贡献。综述正文以问题和主题为基本单位，默认禁止按“作者 A 发现……作者 B 发现……”逐篇罗列；重要综述可以用于建立领域地图，但关键科学判断尽量回到原始论文核验。

研究计划书、开题报告、grant / funding proposal 和既定项目内子课题计划使用独立 Proposal 流程：先锁定 target reader、当前阶段、approved project / supervisor / funder 硬约束和 deferred scope，再直接消费 Akira 已有 Research Tree、Literature、Hypothesis、Design 与 preliminary evidence，而不是另建第二套科研状态。写作严格区分已经建立的事实、合理推断、待检验 Hypothesis、planned action、expected result 与 unsupported claim；“创新点”和“预期结果”只能写未来计划贡献，不能提前写成“已证明/已建立”。可行性必须落到已有 evidence / resource、关键 dependency、failure mode 与 fallback，不能只写空泛保证。

系统综述（Systematic Review）、范围综述（Scoping Review）和荟萃分析（Meta-analysis）不属于“普通综述写作模板”。如果其正式检索、纳入排除、筛选、质量/偏倚评价、数据提取和综合 provenance 尚未完成，必须先退出 Communication 回到科研流程，按当前权威方法学和 reporting guideline 完成并冻结，再回来写作；不能用叙述性综述的写法冒充正式证据综合方法学。

无论选择哪条流程，最终都要检查材料有没有被选择性遗漏、全文大逻辑和段落小逻辑是否成立、citation 是否真实支持对应句子，以及结论强度是否匹配 evidence。段落/section 结构不清时使用反向提纲（reverse outlining）：从 section thesis 反查每个段落的 topic sentence 和 evidence，避免靠连接词把无关段落强行粘在一起。Publication figure 也按科学论证组织：先明确 Figure-level scientific question 和最窄 Claim，再给每个 panel 分配不同证据作用；Main Figure 保留决定性 evidence、必要 control 和会改变解释的 boundary，secondary metric / robustness 等可以进入 Supplement。最终图必须在实际输出尺寸逐 panel 检查 `n`、uncertainty、单位、scale、颜色编码、图注、source-data provenance 和可读性，不能只看绘图源码或缩略图。`communication` 还维护受控的科研写作逻辑表达参考，覆盖递进、转折、对照、因果、解释、举例、让步、综合和结论强度。

长篇 draft 在进入 reviewer-style review 前执行初稿完整性审计；经过实质 revision 后、最终交付前再执行一次最终审计。审计重点是高风险 Claim 与 source 是否匹配、数字/统计是否与 canonical output 一致、scope/limitation 是否漂移，以及修订有没有把 association、mechanism 或 novelty 无依据写强。Reviewer-style 审查先分别检查内部效度、外部效度与科学贡献，再检查方法严谨性、evidence sufficiency、argument coherence、literature integration、复现性与 writing quality；单一关键证据若决定主要结论会提高审查强度，致命 validity failure 也不能靠其他维度的优点或平均分抵消。Citation 另外明确拆成三层：文献身份是否正确、source 是否真的支持当前 Claim、格式是否符合目标 venue；DOI 能解析、metadata 正确或 bibliography 编译成功都不能代替 Claim–source 核验。复合长句应先拆成可核验 Claim 单元，最终稿还要检查 in-text citation 与 reference list 双向对应。无法访问或无法核验的 evidence 保持显式 unresolved，不能为了通过门禁制造 PASS。

Reviewer response / revision 另走意见—动作—证据闭环：先保存 editor / reviewer 原始材料，复合 comment 拆成可独立验收的子要求，不能只处理其中最显眼的一项；每条要求先固定实际验收标准，先检查 revised manuscript、analysis、experiment、figure 等真实 artifact 是否满足，再读取 response letter 判断它是否准确描述修改。Blind review 下 reviewer-facing 回复彼此隔离，不把另一位 reviewer 的 comment、编号或 recommendation 暴露出去。作者“说已经做了”与可检查 artifact “证明已经做了”必须分开；需要新实验或 Analysis 时返回对应科研流程，不在 Communication 中虚构结果。Clean manuscript、marked manuscript 和 response letter 同时交付时视为联动 package，任何稿件编辑都会使旧 quotation、page/section locator 和 package consistency 检查失效，因此最后一次修改后必须重新核验。

投稿阶段的 Data / Code Availability 与 Source Data 也必须从真实 canonical Dataset / Analysis artifact 出发：先盘点 generated、reused public、third-party、restricted data 和 central code，再核验 repository、persistent identifier、version、licence / restriction 与 Figure / Table source-data mapping。临时分享链接不能冒充长期 identifier，“available upon reasonable request”也不能作为默认逃生句；受限数据应说明真实原因、负责 access decision 的主体和申请条件。Communication 不编造 accession、DOI、embargo、ethics permission 或 reviewer access。

连接词用于表达已经存在的推理关系，不替代推理本身；专业术语保持一致，不为了避免重复而随意使用同义词替换。dictionary / thesaurus 可以用于核验普通词汇和固定搭配，但不能自动改写专业概念或升级科学结论。
