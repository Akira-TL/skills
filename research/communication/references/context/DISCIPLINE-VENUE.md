# 学科与目标 Venue 写作叠加层

本文件只在 `WRITING-ROUTER.md` 已先确定文稿类型之后使用。文稿类型决定**科学写作流程**；学科共同体与目标期刊 / 会议（Venue）决定**怎样呈现、强调和审查同一份 evidence**。二者不能倒置。

## 1. 两维路由

先回答：

```text
这是什么传播产物？
→ 原始研究 / 普通综述 / 正式证据综合 / Proposal / 其他
```

再回答：

```text
它写给哪个学科共同体、哪个目标 Venue？
→ 哪些 reporting / rhetorical / artifact convention 当前适用？
```

不得因为某个期刊偏好某种结构，就把普通综述改写成原始研究论文；也不得因为某学科常见某种统计或图表，就反过来改变已经冻结的 estimand / Analysis scientific intent。

## 2. Venue 规则必须从当前权威来源核验

目标 Venue 已知时，通过 `research-standards` 核验当前官方 Author Instructions、reporting guideline、artifact / data / code policy、匿名要求、长度和提交包要求。旧论文、第三方博客、模板仓库和模型记忆只能用于发现线索，不能替代当前官方规则。

若目标 Venue 尚未确定，只采用该学科较稳定的通用表达与审查重点，不提前伪造具体字数、section 名、图表上限或提交附件要求。以后 Venue 确定后重新核验。

## 3. Discipline overlay 只改变强调重点

以下仅用于说明不同共同体常见的审查重心，不是固定模板：

### 自然科学 / 生物医学

通常重点检查：

- independent experimental / observational unit；
- sampling、control、endpoint、effect size 与 uncertainty；
- protocol / assay / measurement reproducibility；
- biological / clinical significance 与 statistical evidence 的区分；
- ethics、registration、reporting guideline、Data / Code / Source Data。

### 计算机科学 / AI / 机器学习

通常重点检查：

- task definition、dataset split 与 data leakage；
- baseline 是否公平、训练 / 推断设置是否可比；
- ablation、sensitivity、robustness、generalization；
- benchmark saturation、compute / model / dataset version；
- empirical gain 是否支持宣称的 mechanism / general capability。

### 人文社会科学与解释性研究

通常重点检查：

- 核心 thesis / conceptual distinction 是否稳定；
- source / corpus / case selection 与解释边界；
- counterargument 与 alternative interpretation 是否被真实处理；
- 证据如何从文本、档案、访谈、田野或案例推进到论点；
- 同一概念跨理论传统时是否发生未说明的语义漂移。

### 跨学科研究

不能把多个领域的惯例简单相加。先确定每个主要 Claim 的 home discipline、measurement / inference tradition 和目标受众，再决定术语、方法说明深度和证据展示方式。若两个框架不可直接通约，按 Literature / Interpretation 的 framework boundary 并列保留，而不是为了“跨学科”强行统一。

## 4. 不维护无限学科模板库

Akira 不为每个学科复制一套完整论文 Skill。稳定的科学合同留在对应 Document Type workflow；学科 / Venue 叠加层只补当前任务真正需要的 convention。

若某一高度专业领域需要成熟软件、数据库或专用写作/报告知识，而 Akira 当前规则不足，可以按 `akira-research` 的 external Skill policy 提议项目级安装单个已审计 Skill。第三方 Skill 仍无权改变 canonical evidence 或科研决策。

## 5. 写作前最小检查

正式起草前至少明确：

- Document Type 已确定；
- target discipline / audience 已知到足够程度；
- target Venue 已知时，当前官方要求已核验；
- 未知 Venue 时没有凭经验写死具体 submission rule；
- discipline / venue convention 不会把 evidence level 或 scientific scope 写强。

若不同 Venue 选择会实质改变主文结构、篇幅、匿名、Data/Code、图表或 Supplement 策略，而用户尚未选择目标，则先呈现这个真实分叉，再决定是否继续写正式投稿版本。