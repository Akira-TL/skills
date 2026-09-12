# 科研稿件 Citation Audit

本文件用于论文、综述、学位论文、报告和 reviewer revision 中的正式 citation audit。Citation audit 必须把**文献身份（identity）**、**Claim 支持关系（claim-source fit）**和**格式（citation style）**分开检查；三者任一成立都不能替代另外两者。

## 1. 三层检查不能混为一个“引用正确”

### 1.1 文献身份

确认 citation 指向的确实是目标论文 / 数据资源 / 标准 / 书籍。至少核对可用的：

- title；
- author / author order；
- year；
- journal / venue；
- volume / issue / pages 或 article number；
- DOI / PMID / PMCID / accession 等稳定 identifier。

DOI 能解析只证明“这个 DOI 对应某个对象”。必须继续比较 DOI 返回记录和当前 reference 的 title / authors 等身份字段；**DOI 能解析但指向另一篇论文属于严重 identity error**。

遇到 Early Access、online-first、正式卷期或不同 metadata provider 记录不一致时，不凭旧引用字符串猜最终值。优先核对当前 publisher / DOI registration / authoritative bibliographic source，并明确哪些字段是出版状态变化而不是文献身份变化。

如果只有标题、作者、年份或 citation string，优先调用 `literature-access` 的 identity resolution；多个候选无法唯一确定时保持 unresolved，不能选一个最像的条目继续。

### 1.2 Claim 支持关系

Identity 正确不代表 citation 支持当前句子。对每个实质 Claim 继续检查：

- source 的哪一段、哪张图、哪项结果或哪条正式规则支持它；
- citation 支持整句，还是只支持其中一个从句 / 数字 / 背景事实；
- source 报告的是直接 observation、作者 interpretation，还是 review 中的二手总结；
- population、timeframe、measurement、causal level 和 certainty 是否一致；
- 当前稿件有没有把 `associated with`、`consistent with` 等写强为因果或机制。

搜索结果标题、abstract snippet、数据库 metadata 或“主题相关”都不能作为 Claim support 的充分证据。关键 Claim 需要回到可核验的原始来源；若 source 只能访问摘要，则按实际可核验范围限制结论。

### 1.3 引用格式

格式规则只在 identity 与 support 已经合理后处理。根据目标期刊 / 学位 / 报告要求，通过 `research-standards` 核验当前 citation style、reference list 规则和投稿阶段要求；不要因为没有显式指定就默认套 APA、Nature 或其他某一格式。

格式检查包括适用时的：

- in-text citation 和 reference list 是否双向对应；
- author、year、编号或 citation key 是否一致；
- 同作者同年份的区分是否一致；
- DOI / URL / accession 的展示方式；
- journal abbreviation、title case、pages / article number；
- reference order 与 numbering；
- direct quotation 所需 locator。

只有纯格式、且 correction 唯一确定时才可以机械修正；一旦修改会改变文献身份或 Claim attribution，就必须回到 identity / support 检查。

## 2. 先把长句拆成可核验 Claim 单元

Citation audit 的基本单位不是“整段有没有几个引用”，而是一个 citation 实际承担了哪些 Claim。

当一句话同时包含多个独立事实，例如：

```text
X 在 population A 中升高，并导致 Y，且这种机制在 population B 中也成立。
```

不能因为句末有一个 citation 就默认它支持全部内容。应先拆解为独立可核验部分：

```text
Claim A：X 在 population A 中升高
Claim B：X 导致 Y
Claim C：该机制在 population B 中成立
```

再分别判断需要哪些 source。若不同 Claim 需要不同 citation，正文应通过拆句、局部 citation 或更清楚的语法范围表达对应关系。

综述中的 citation cluster 也一样：一组引用必须共同支持前面的综合判断，而不是“这些论文都与主题相关”。

## 3. Reference identity audit 的优先顺序

对正式稿件中的 reference，优先从成本低且可确定的检查开始：

1. 有 DOI / PMID / PMCID / accession → 先解析 identifier；
2. 比对 title、authors、year 和 venue，确认 identifier 没有张冠李戴；
3. 缺 identifier 或解析失败 → 用 title + author + year 做 exact-work resolution；
4. 多来源 metadata 不一致 → 优先 publisher / authoritative registry，并保留 unresolved difference；
5. 无法唯一定位 → 标记 `unverifiable identity`，不能补造 DOI、pages、authors 或 year。

Reference list 中的作者漏写、顺序变化、article number 与 page 混淆、DOI 指向另一论文、title 核心词不匹配等都属于 identity 问题，不应只作为“格式错误”自动修正。

## 4. In-text citation 与 reference list 双向核对

最终稿至少检查：

```text
每个 in-text citation → 有且只有合理对应的 reference entry
每个 reference entry → 确实在正文 / figure / table / supplement 的适当位置被引用，或有明确保留理由
```

重点发现：

- orphan in-text citation；
- orphan reference；
- author / year / number 不一致；
- revision 后 numbering / citation key 漂移；
- 删除段落后 reference list 仍保留无用途条目；
- 新增 reference 但正文实际没有建立 support relation。

“reference list 里有这篇论文”不代表正文已经正确引用它。

## 5. 文献状态风险与不可核验情况

当 citation 对核心 Claim 很重要时，如果当前权威来源显示 retraction、withdrawal、expression of concern、重大 correction 或版本变化，应明确判断这些状态是否影响被引用的具体结论；不能只因为 reference metadata 仍可解析就忽略状态变化。

若无法访问足够信息判断：

- 保持 `unresolved / unverifiable`；
- 说明缺的是 identity、full text、specific result 还是 publication status；
- 核心 Claim 不能在 unresolved support 上继续写成确定结论；
- 可以返回 `literature` / `literature-access` 补齐 source。

## 6. 不采用机械 citation quota

Akira 不把下列经验值作为通用科研规则：

- “自引超过固定百分比就一定有问题”；
- “超过固定年限的文献就应替换”；
- “每个 paragraph 必须至少有一篇 citation”；
- “一句话超过固定数量 citation 就属于 over-citation”。

真正检查的是：

- citation 是否必要；
- 是否引用了提供该事实的合适来源；
- 是否遗漏关键 foundation / contradictory evidence / current evidence；
- 是否存在不当自引、citation coercion 或引用堆砌的实际迹象；
- publication target 是否有明确规则。

领域基础论文可以很旧，原创 Methods / Results 段落也可以不需要外部 citation；反过来，一个综合判断可能合理需要多篇文献。

## 7. Revision 后 citation 必须重新审计

任何可能改变以下内容的 revision 都会使旧 citation audit 部分失效：

- 新增 / 删除句子或 Claim；
- 调整 Claim strength；
- 移动 citation 的语法作用范围；
- 增删 reference；
- 修改 figure / table / supplement 中的 citation；
- reference numbering 或 bibliography 重新排序。

最终 revision audit 要重新检查：

```text
manuscript Claim
↔ in-text citation
↔ reference identity
↔ source support
↔ reference-list entry
```

不能只确认 bibliography 编译成功。

## 8. Citation Audit 完成条件

正式交付前至少确认：

1. 核心 citation 的 identity 已解析，identifier 没有张冠李戴；
2. 高风险 / 主要 Claim 能定位到实际 source support；
3. compound Claim 没有被一个“主题相关” citation 一次性包办；
4. in-text citations 与 reference list 无未解释 orphan；
5. publication status 的已知重大风险已处理；
6. citation style 来自当前目标规范，而非 Agent 默认偏好；
7. 无法核验的关键 reference / Claim 明确保持 unresolved；
8. revision 后重新检查了 citation drift。

Citation Audit 证明的是当前稿件中已经检查到的引用关系在明确范围内一致，不证明所有语义 Claim 被穷尽，也不替代 Literature Reconstruction / Critical Audit。
