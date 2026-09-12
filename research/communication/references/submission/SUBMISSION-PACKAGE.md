# 科研稿件 Submission Package 工作流

本文件用于期刊 / 会议正式投稿、重新投稿和最终 submission package 准备。目标不是套一个通用投稿模板，而是把**目标 venue 当前要求、已经完成的科研稿件、真实作者 / 合规 / 数据事实和所有提交文件**组合成彼此一致、可核验的交付包。

具体期刊的作者指南、文章类型、匿名规则、word / figure limit、declaration、AI disclosure、伦理、data/code、reviewer suggestion、cover letter、checklist、文件格式和投稿阶段要求都必须通过 `research-standards` 或当前官方 Author Instructions 核验；不要依赖第三方仓库中缓存的期刊规则或模型记忆。

## 1. 先确认 target venue、article type 与 submission stage

准备文件前明确：

```text
target journal / conference
article type
submission stage
first submission / transfer / resubmission / revision / accepted-stage
single-anonymous / double-anonymous / open review（若适用）
current author instructions / policy source
```

不同阶段的文件要求不能混用。例如 initial cover letter、revision response、accepted-manuscript source files 和 production proof 是不同交付物；不要因为以前某个阶段要求某文件，就默认当前阶段仍要求。

如果目标 venue 尚未确定，可以准备 venue-neutral manuscript，但不能假装已经知道 citation style、word limit、cover letter、declaration 或 file format。

## 2. 建立 Deliverable Matrix

根据当前官方规则建立最小交付矩阵，例如：

| Deliverable | Required / Optional / N/A | Source of requirement | Current artifact | Missing input / action |
| --- | --- | --- | --- | --- |
| Main manuscript |  |  |  |  |
| Anonymous manuscript |  |  |  |  |
| Title page |  |  |  |  |
| Cover letter |  |  |  |  |
| Figures / tables |  |  |  |  |
| Supplement |  |  |  |  |
| Reporting checklist |  |  |  |  |
| Author contributions |  |  |  |  |
| Funding / COI / ethics |  |  |  |  |
| Data / Code Availability |  |  |  |  |
| Reviewer suggestions |  |  |  |  |
| Permissions |  |  |  |  |
| Other venue-specific files |  |  |  |  |

不要求所有 venue 都有上述条目。只有当前官方说明要求或实际适用的项目进入 package。

## 3. 行政与合规事实不得由 Agent 推断

下列事实如果没有用户、机构文件、正式 project record 或其他可核验来源，必须标成 `AUTHOR_INPUT_NEEDED` / unresolved，不得补造：

- author name / order / affiliation / present address；
- corresponding author 和 contact；
- ORCID；
- equal contribution / senior authorship；
- author contribution roles；
- all-author approval；
- grant / funding body / grant number；
- funder role；
- competing interests；
- ethics / IRB / animal / biosafety / permit approval 与编号；
- informed consent / publication consent / exemption；
- clinical / prospective study registration；
- data / material / code licence 与 access permission；
- third-party image / figure / questionnaire / dataset permission；
- preprint、related manuscript、prior submission、concurrent submission status；
- AI / LLM use disclosure requirement 与实际使用事实；
- suggested / opposed reviewer 的 conflict status。

Communication 可以帮助组织和措辞这些事实，但不能让一段流畅 declaration 变成事实来源。

## 4. Authorship、contribution、funding 与 COI 分开处理

作者资格、贡献角色、funding、acknowledgement 与 competing interests 是不同问题。

- author list 依据目标 venue / discipline 当前适用的 authorship policy；
- contribution taxonomy（如 CRediT）只在 venue / funder / collaboration 实际采用时使用，并由作者确认实际角色；
- “提供资金 / 设备 / 行政支持”等是否构成 authorship，按当前适用标准和真实贡献判断，不由 Agent 自动套规则；
- Funding statement 只描述实际支持来源和 funder role；
- Competing-interest statement 描述可能影响独立性的关系；两者不能合并成同一 disclosure；
- acknowledgements 不能用来隐藏应披露的 funding / COI，也不能把没有确认的人列入感谢。

如果 funder 要求特定 acknowledgement / disclaimer，必须从当前正式 award / funder guidance 核验原文，不凭第三方模板生成“看起来像官方”的措辞。

## 5. Ethics / registration / regulated research 只做 applicability routing，不补造批准

投稿前根据研究类型调用 `research-standards` 判断是否涉及：

- human participants / identifiable data；
- animals；
- clinical trials / prospective intervention；
- sensitive / controlled data；
- biosafety / dual-use / regulated materials；
- protected sites / samples / permits；
- specialized structure / sequence / taxonomy deposit；
- image-integrity / original-data requirements；
- 其他领域特定合规文件。

对每一项只允许三种状态：

```text
verified applicable and documented
verified not applicable
AUTHOR_INPUT_NEEDED / unresolved
```

不能从 Methods 中“看起来做过伦理审批”就编 approval number；也不能因为稿件没写就断言未审批。缺失的真实 approval / registration / consent 可能构成科研实施层面的 blocker，应返回 `study` / 项目 owner，而不是只在 Communication 中补一句声明。

## 6. Anonymous 与 identified files 必须系统分离

若 venue 使用匿名审稿，按当前规则检查匿名稿中是否应删除 / 泛化：

- author names / affiliations；
- corresponding-author details；
- acknowledgements / grants；
- self-identifying repository / institution wording；
- author contribution；
- document metadata / tracked-change author identity；
- Supplement / Figure / file properties 中的身份信息；
- cover letter / title page 与 anonymous manuscript 的分离要求。

但匿名不能以篡改 scientific provenance 为代价。例如 self-citation 的匿名方式、institution name 是否需遮蔽、repository 是否允许 temporary anonymous link 都按 venue 当前规则处理，不能自行把关键 Methods 改成不可复现。

## 7. Cover letter 是编辑沟通，不是第二份 Abstract

只有 venue 需要或接受时才准备 initial cover letter。它通常应准确说明：

```text
稿件是什么 article type
回答什么问题
最主要发现 / contribution
决定性 evidence 是什么
为什么和该 venue 的 scope / readership 匹配
需要披露的 related manuscript / preprint / conflict / originality 等事实
```

规则：

- 不重复整篇 Abstract；
- novelty / priority 继续受 Literature / Citation Audit 约束；
- 不写 “first / unprecedented / groundbreaking” 来替代 evidence；
- 不通过 name-dropping editor / reviewer / famous scientist 施加说服；
- journal fit 必须对应真实 scope / readership，而不是空泛“prestigious journal”；
- required originality / author approval / simultaneous-submission 等声明只有真实确认后才能写。

Revision cover letter / response letter 走 [`../REVISION-WORKFLOW.md`](../REVISION-WORKFLOW.md)，不要和 initial submission cover letter 混用。

## 8. Reviewer suggestions 需要真实 expertise 与 conflict check

只有 venue 请求 / 允许时处理 suggested or opposed reviewers。候选至少核验：

- 当前姓名、机构、可验证 professional contact；
- 与稿件 topic / method 的实际 expertise；
- venue 定义下的 recent coauthorship、same institution、supervisory、close collaboration、financial / personal conflict 等；
- opposed reviewer 的理由是否事实性、专业且不攻击人格。

Agent 可以帮助发现候选，但不能替作者确认所有未公开 conflict。若 conflict status 需要作者知识，明确请求用户确认。

## 9. Declarations 要跨文件保持一致

同一事实在 title page、manuscript、submission form、cover letter、Supplement 和 repository 中出现时必须一致。例如：

- manuscript title / running title；
- author order / affiliation mapping；
- grant number / funder；
- ethics / registration ID；
- Data / Code Availability；
- COI；
- article type；
- manuscript / figure / table / supplement count；
- related manuscript / preprint status。

如果 submission system 要求单独填写字段，不能因为 manuscript 已经写过就默认 portal 值会自动同步；反之也不能只填 portal 而遗漏 venue 要求在 manuscript 中出现的 declaration。

## 10. Data / Code / Source Data 单独执行 availability workflow

所有 availability statement、repository、accession、licence、restricted access 与 Figure / Table source-data mapping 按 [`DATA-AVAILABILITY.md`](DATA-AVAILABILITY.md) 执行。Submission Package 只检查它是否是当前 venue 所需 deliverable，以及在所有文件中的 identifier / wording 是否一致。

## 11. Figure / Supplement / checklist 是 package 的一部分，不是附件尾声

正式提交前检查：

- manuscript 中每个 Figure / Table / Supplement citation 都有对应文件；
- 文件编号、panel label、legend 与正文一致；
- Supplement 中的 Methods / Tables / Figures 与正文 cross-reference 不漂移；
- publication Figure 已通过 [`../FIGURE-WORKFLOW.md`](../FIGURE-WORKFLOW.md)；
- applicable reporting checklist / reporting summary 与 manuscript 实际内容一致，而不是为了打勾填写稿件没有报告的内容；
- third-party material 的 licence / permission 已真实取得或按 venue 合法处理；
- image / source-data / raw-data requirements 按当前领域 / venue policy 检查。

## 12. AI / software / editing disclosure 只按当前政策和真实使用情况写

AI / LLM、language-editing service、automated screening、statistical software 或其他工具的 disclosure 要求变化较快，必须查询当前 venue / funder / institution policy。

规则：

- 不把 AI / software 列作作者，除非未来某个正式政策明确允许且当前 venue 接受；当前具体要求必须实际核验；
- 不隐瞒 venue 明确要求披露的实际使用；
- 不为了“保险”编造没有发生的 AI use；
- disclosure 说明真实用途和 human verification，不把 Agent 自己生成的科研判断描述成已有人类独立验证，除非确有该过程；
- confidential manuscript / peer review / sensitive data 是否允许上传外部服务，按当前 confidentiality / data policy 和实际工具边界处理。

## 13. Submission Package 一致性审计

在提交前，对所有 required artifact 做一次 cross-file audit：

1. target venue / article type / submission stage 是当前真实目标；
2. deliverable matrix 没有 unresolved required item；
3. author names/order/affiliations/contact 在所有 identified files 一致；
4. anonymous 文件没有违反当前 blind-review policy 的身份泄漏；
5. title / abstract / keywords / article type 在相关文件一致；
6. Figure / Table / Supplement 完整且正文都有正确 locator；
7. citations / bibliography 通过 [`../audit/CITATION-AUDIT.md`](../audit/CITATION-AUDIT.md)；
8. funding / COI / ethics / registration / permissions 都来自已确认事实；
9. Data / Code Availability 指向真实 destination；
10. cover letter 的 Claim、novelty 和 venue fit 与 manuscript 一致；
11. reporting checklist 没有声明稿件不存在的方法或信息；
12. suggested reviewers 的 identity / expertise 已核验，作者已确认必要 conflict；
13. manuscript source / rendered PDF / supplement 已按 [`RENDERED-OUTPUT-QA.md`](RENDERED-OUTPUT-QA.md) 在当前目标格式执行 build / render / page-level 检查，无 unresolved citation / reference / missing asset、blocking clipping / overlap / unreadable evidence；
14. 所有 placeholder / `AUTHOR_INPUT_NEEDED` 在提交版中已解决，或 package 明确不能提交。

## 14. Readiness

可以用三个工程状态描述 package，而不是给稿件科学质量打分：

- `ready`：当前 venue 要求的全部交付物与事实已齐，并完成一致性检查；
- `needs_author_input`：文稿本身可继续准备，但至少一个必须由作者 / institution 确认的事实尚缺；
- `blocked`：缺少不可由 Communication 修复的关键 ethics / registration / permission / authorship / integrity / repository / required scientific artifact。

这些状态只表示 submission package readiness，不表示论文会被接受，也不替代科学 integrity audit。
