# 第三方科研 Skill 多轮审计与吸收记录

本文件记录 Akira Research 对外部科研 Skill 的职责判断、已吸收方法、明确拒绝项与运行时边界。它不是第三方源码镜像；第三方正文、schema、模板和 Agent pipeline 不复制进 Akira。

最近审计日期：2026-09-12。

## 1. 总原则

第三方科研 Skill 只在能补足 Akira 现有 owner 的情况下提供方法启发。吸收时遵守：

1. **先找 owner，再吸收规则**：已有 `literature`、`design`、`analysis`、`interpretation`、`communication`、`research-standards` 或其他明确 owner 时，把有价值的方法并入现有职责，不新建平行 Router。
2. **吸收科研方法，不复制第三方流水线**：外部 Agent roster、prompt persona、状态机、专属 schema、模板、评分器和内部 marker 默认不进入 Akira。
3. **科研有效性优先于机械分数**：固定论文数量、数据库数量、轮次、字数 buffer、A–F 总评分或单一 metric 不能替代 Claim-specific evidence judgement。
4. **期刊特定规则不升级成全局科研规则**：Nature、Nature Communications 或其他 venue 的格式、编辑偏好和投稿要求，只在当前目标 venue 的官方规则确实适用时通过 `research-standards` 核验。
5. **第三方来源不成为科研 authority**：伦理、注册、数据保护、报告指南、期刊要求和软件行为仍回到当前权威来源核验。
6. **已有 Akira provenance 更强时不降级**：若 Akira 已由 `research.sqlite`、Git、Research Tree、Analysis Attempt 或 canonical artifact 提供更强状态与追溯能力，不再引入第二套“真相源”。
7. **license 决定可吸收方式**：允许参考的方法仍需由 Akira 独立重写；限制性 license 下不复制正文、schema、模板或实现。

只有外部项目出现新的、与当前 Akira owner 不重复且能修复真实工程/科研缺口的能力时，才重新扩大审计范围。不能为了“继续吸收”而机械增加规则。

## 2. `leo-lilinxiao/codex-autoresearch`

审计 revision：`d65f7c6c6718e9b795e97b907d09a4e361b32a1f`

仓库 license：MIT。

### 已吸收

吸收进 `analysis` / Analysis Attempt 的方法：

- 只在存在稳定、可重复机械指标的问题上使用受控迭代；
- 第一次修改前固定 baseline、metric、优化方向、target 与 guard；
- 每个 Attempt 只做一个主要、可解释的变化，保证结果可归因；
- metric 改善但违反 guard、统计前提、数据边界或 scientific validity 时不得选用；
- benchmark / verify 本身噪声过大时先修测量方法，不把随机波动解释成改善；
- 有效但未改善的执行仍保留为 `abandoned`，违反前提的执行标记 `invalid`，不只保存“最好的一次”；
- 执行状态必须 fail closed，不能靠会话记忆补造缺失状态。

Akira 的实现继续由 Analysis Attempt、Git commit、config、output、decision reason 和 `research.sqlite` 提供 provenance。

### 明确不吸收

- 不让第三方 controller 接管科研 branch 的 commit / revert 生命周期；
- 不把自动 `git revert` 当成 Akira 科研路线的通用失败处理；
- 不对已经进入科研 provenance 的 commit 做 reset / amend / rebase 等历史改写；
- 不把“一个数值更好”自动等同于 scientific validity；
- 不把开放式探索、机制判断、方法选择或“哪种结果更显著”强行压成单一优化分数；
- 不再引入第二套 run/event state 作为 Analysis Attempt 之外的权威状态源。

运行时定位：`reference-only / isolated-only`，不是 Akira Research 的默认执行依赖。

## 3. `Yuan1z0825/nature-skills`

审计 revision：`c4e4c99fbeaf0168cda090f8739e1508017a610e`

仓库 license：Apache-2.0。

### 已吸收

主要吸收进 `communication`、`scientific-presentation-authoring` 与 `research-standards`：

#### 论文论证与写作

- 原始研究论文先固定主要结论与 evidence boundary，再建立 Results evidence chain；不按 Figure 顺序平铺结果；
- paragraph flow 以一个段落一个主要推理任务为基础，并使用 reverse outlining 检查 section thesis、topic sentence 与 evidence 的关系；
- Title、Abstract、Conclusion 和其他压缩表面不得因为删字而丢失会改变 Claim 真值、scope 或条件性的限定语；
- Supplement 承接次级证据与复现材料，但不能用来隐藏会改变主要结论的 negative evidence / failure boundary。

#### 投稿前审查与修订

- draft 在 reviewer-style review 前做完整性审计，实质 revision 后再做最终 drift 审计；
- reviewer comment 必须映射到实际 manuscript / citation / analysis / experiment / Figure / Claim adjustment，response prose 本身不是完成证据；
- re-review 先固定 concern 的验收标准，独立检查 revised artifact，再读 response letter，避免被作者说服性文字锚定；
- 多视角 reviewer-style 自审先冻结共同输入，各视角分别形成 concern 后再综合；没有真实上下文隔离时只能称多视角审查，不能声称独立/盲审 reviewer；
- reviewer concern 区分最低限度的诚实修复、更强但代价更高的补强方案，以及没有写作性补救的致命问题；
- manuscript 级终检检查术语、样本数、单位、小数精度、Methods↔Results、Abstract↔正文、Figure/Table cross-reference 等跨全文一致性。

#### 投稿包与最终输出

- submission package 按当前 venue 官方规则建立 deliverable matrix，跨 manuscript、cover letter、declarations、Figure、Supplement 和 submission metadata 检查一致性；
- rendered PDF / DOCX / PPTX 的实际页面是排版交付事实；source 看起来正确不能替代编译/转换、日志检查、逐页渲染 QA 与再次渲染；
- paper-to-presentation 按论文类型、科学问题、关键 evidence、robustness、limitations 和 Figure traceability 组织，不机械把整篇论文逐图搬进幻灯片。

#### 科研图像完整性

- 图像处理 provenance 与图像处理是否科学允许是两件事；
- 原始科研图像、采集 metadata 与处理步骤应保持可追溯；
- crop、contrast、pseudo-color、channel adjustment、stitching / assembly 等处理必须保持科学含义并在适用时披露；
- 不允许通过 clone、healing、generative fill、选择性 erase 或局部处理隐藏/制造 evidence；
- 不同时间、视野、样本或条件取得的图像不能拼成貌似连续的 observation 而不标明边界。

### 明确不吸收

- Nature / Nature Communications 专属编辑标准、栏目结构、格式数值、LaTeX float 参数或 submission UI 规则不升级成 Akira 全局规范；
- “broad readership”“outstanding importance”“interdisciplinary interest”等只在目标 venue 当前官方评价标准确实要求时使用；
- 不安装第二套 Nature writing / reviewer / response Router 与 Akira Communication 并行竞争；
- 不复制 Nature 风格 phrasebank、固定段落模板或 Figure 模板；
- 不把特定期刊要求的 gel/blot 附件、结构文件或专用表单写死成所有项目的通用科研门禁；这些继续由 `research-standards` 按适用性核验。

运行时定位：`absorbed-reference`；不作为平级科研 Router 安装。

## 4. `Imbad0202/academic-research-skills`

审计 revision：`f1a57bbcabf5cf3da9654ac4d54d056dc6b4b7ea`

仓库 license：Creative Commons Attribution-NonCommercial 4.0 International（CC BY-NC 4.0）。

因此 Akira **只吸收方法思想并独立重写规则，不复制其正文、schema、模板、固定清单或 pipeline 实现。**

### 已吸收

#### Claim、citation 与 integrity

- citation identity 正确不等于 citation 真正支持对应正文 Claim；必须做 claim-to-source 核验；
- headline、numerical、causal、methods-critical、disputed Claim 属于优先核验对象；
- 无法访问或无法核验的 source 保持 `unresolved / unverifiable`，不能用缺失信息制造 PASS；
- 实质 revision 后重新检查 Claim strength、数字、scope、limitation 与 citation drift；
- “作者/用户说已经完成”与“可核验 artifact 证明已经完成”保持分离。

#### Literature 的反证与综合

- 当前 Active Uncertainty 已有主要 Claim、竞争解释或方法路线时，Discovery 主动安排至少一轮以推翻或限定当前判断为目的的检索；
- 主动找相反结果、失败复现、negative/null evidence、边界条件、方法批评和竞争解释；
- 反证检索零命中也保存真实 Search Run 与检索边界，但“没搜到”不能升级为“不存在反证”；
- 跨学科综合前先核对 construct、measurement、unit、population、time、estimand / inference target 是否可比；
- 同词不等于同一科学对象，不同词也不自动代表不同 construct；不可通约的框架并列保留，禁止为了生成统一 narrative 制造假共识或假冲突。

#### 受监管科研的 authority boundary

- 规范本身的内容与“该规范是否适用于当前项目”分开；
- applicability 至少区分适用、不适用和未知，`unknown` 不能静默变成 `not applicable`；
- Agent 不从作者语言、所在地区、机构名称、研究主题或 manuscript prose 猜 IRB / REC、数据保护、试验注册、permit、exemption 等 authority 结论；
- exemption route 存在不等于项目已经获得 exemption；
- 多个 jurisdiction、institution、funder 或 regulator 的要求冲突时并列保留，交给相应 authority / 用户确认，不由 Agent 私自“取最严格”或“取最宽松”。

#### 预注册边界

- Akira 内部结果前 Git freeze / Design freeze 只证明项目内部版本在结果可见前已经固定；
- 它**不等于**外部 preregistration、trial registration、protocol registration 或 Registered Report 的 Stage 1 acceptance；
- 外部注册状态必须有对应 registry / journal / institutional provenance；
- 是否必须注册、应使用哪一 registry、时点要求和披露义务，由 `research-standards` 从当前正式规则核验。

### 明确不吸收

- 不引入完整 research→write→review→revise→finalize 多 Agent state machine；
- 不引入第二套 Research Router、数据库 schema、Agent roster、handoff passport 或 pipeline artifact system；
- 不采用固定 Evidence Pyramid 作为跨学科全局证据等级；证据质量继续取决于当前 Claim、design、measurement、bias 与 discipline-appropriate method；
- 不采用 A–F 总评分、固定年份区间或加权总分来替代 Critical Audit；
- 不要求固定论文数、数据库数、搜索结果数、技术方案数或 reviewer 数；
- 不采用“revision 超过 N 轮就强制完成并把 major issue 塞进 limitation”的规则；未解决的 validity failure 仍是未解决；
- 不复制 30+ logical-fallacy catalog；只把会改变科研判断的推理检查并入现有 Evidence Gate / Critical Audit；
- 不新增 WHY / HOW / WHAT `three-way-scan`，因为 Akira Literature 的 Reconstruction、Critical Audit 和固定人类阅读结构已经覆盖且更细；
- 不新增第三方 `claim_intent_manifest`，因为原始研究写作已经在 prose 前固定主要结论、主要 evidence、scope、关键限制/反证与 evidence level，并据此搭 Results 骨架；
- 不采用固定 whitespace word-count 算法和 3–5% buffer 作为全局投稿规则，字数/字符数以当前 venue 的实际规则和投稿系统为准；
- 不采用 `[direct-mode]`、固定入口澄清菜单等第三方 Router 协议；Akira 继续依据用户明确目标与 canonical scientific state 路由。

运行时定位：`absorbed-reference / blocked-runtime-router`。

## 5. `K-Dense-AI/scientific-agent-skills`

审计时上游 HEAD：`c1ed16d97dd61ff50a3bd46dd353e4a55fd77f34`。

仓库 README 标示整体 MIT，但同时存在 vendored / community Skill；**安装前仍必须检查具体 Skill 自己的 license、脚本、网络行为、凭据需求和外部依赖。**

定位：`project-local-on-demand`。

- 不加入 Akira Lattice submodule；
- 不加入全局 `install.sh`；
- 不批量安装；
- 当前任务需要某一专业能力时，只审计那个具体 Skill；
- 确认它只补执行知识、不接管 Akira scientific decision / provenance 后，再向用户请求项目级安装许可；
- 安装命令与权限边界见 [`POLICY.md`](POLICY.md)。

## 6. 当前 Akira owner 对照

| 外部能力面 | Akira owner | 当前处理 |
| --- | --- | --- |
| 可量化机械迭代 | `analysis` / Analysis Attempt | 已吸收，Akira Git/SQLite 保持权威 |
| 文献发现与证据综合 | `literature` | 已吸收反证检索、框架可比性；拒绝固定篇数/评分器 |
| Research Design / 结果前冻结 | `design` | 已区分内部 freeze 与外部 preregistration |
| 受监管科研规范适用性 | `research-standards` | 已加入 authority / applicability boundary |
| Scientific Claim 解释 | `interpretation` | 继续使用 competing hypotheses、alternative explanations 与 scope gate |
| Manuscript drafting | `communication` | 已吸收 evidence chain、reverse outlining、compression integrity |
| Citation / integrity audit | `communication` | 已吸收 claim-to-source、drift、consistency audit |
| Reviewer-style review / revision | `communication` | 已吸收 evidence-before-persuasion、隔离审查与 remedy tier |
| Figure / image integrity | `communication` | 已吸收 Figure evidence role、最终尺寸 QA 与原始图像完整性 |
| Submission package | `communication` + `research-standards` | 已吸收 deliverable matrix；venue 规则动态核验 |
| Paper presentation | `scientific-presentation-authoring` | 已吸收按论文类型和 evidence narrative 组织汇报 |
| 专业软件/领域工具 | `K-Dense` 单 Skill（项目级、按需） | 不做默认全局依赖 |

## 7. 本轮停止条件与后续复审

截至本次审计，前三个重点外部仓库的剩余内容主要属于：

- Akira 已有更强 owner 的重复规则；
- 特定期刊格式和模板；
- 固定评分器、固定数量阈值和经验性配额；
- 第三方 Agent orchestration / handoff / schema 工程；
- 外部 API 的具体适配协议；
- 已被 Akira Git + SQLite provenance 覆盖的第二套状态系统。

因此当前停止继续逐文件吸收。以后只有满足以下至少一项才重新开启深审：

1. 外部仓库出现新的科研能力面，Akira 目前没有明确 owner；
2. Akira 黑盒验收暴露真实缺口，而外部实现提供了可验证的解决思路；
3. 某具体专业任务需要 K-Dense 或其他仓库中的领域 Skill；
4. 目标 venue / regulator / reporting guideline 发生变化，需要重新核验当前适用规范。

复审时仍从当前上游 revision 和 license 重新开始，不默认沿用旧审计结论。
