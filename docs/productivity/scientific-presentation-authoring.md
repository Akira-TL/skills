# scientific-presentation-authoring

## 用途

`scientific-presentation-authoring` 用于创建、改写和审阅科研或学术类 PPT 的内容结构、页面文案与版式逻辑。它适合研究汇报、论文汇报、答辩、组会、研究计划等场景，也适合在用户提供参考 PPT 时提取其中的写作和视觉规则，再为当前研究重新组织页面。

这个 Skill 不把参考 PPT 当作模板素材库。它只提取标题层级、页面密度、留白、网格、图文比例、章节组织和结果页写法等规则，不复制参考文件中的校徽、示例文字、图片、占位符或无关页面结构。

## 主要行为

Skill 会先把研究材料拆成背景、目标、章节、样品设计、方法、结果、可行性和进度等语义对象，再决定页面顺序和页数。原始文件页码不会自动成为新 PPT 的页面结构。

当输入是一篇论文、预印本或结构化文献阅读结果时，先恢复论文的 scientific argument，再根据 discovery / mechanism、methods / algorithm、resource / dataset、clinical / population、materials / engineering 或 review / evidence-synthesis 类型选择汇报叙事。Figure 按 central evidence、control / robustness、validation、boundary 等科学作用筛选，不要求按论文 Figure 1、Figure 2 顺序全部搬运；关键裁剪必须保留 axis、unit、legend、panel label、scale bar 和统计标记，并能定位回原 Figure / Table / Supplement。作者解释与汇报者自己的 Critical Audit 分开表达。

结果页默认只写可直接由图表或正式结果支持的内容，包括观察结果、组间差异、数值、范围、样本量、显著性和分析阈值。普通结果页的标题描述“分析什么”，不把机制解释或结论直接写进标题。诸如“说明”“提示”“揭示”“驱动”“机制”“传播”“适应”等解释性表述留给专门的讨论、总结或结论页，并且必须有相应证据。

中文页面文案完成后，Skill 会按 `humanizer-zh` 的规则清理 AI 写作痕迹，删除空泛的意义句、公式化排比、宣传式动词和抽象总结，同时保持研究事实、统计结果和术语不变。

## 页面组织

当研究已经按章节组织时，Skill 会保留章节结构，并使用连续的小节编号，例如 `3.1`、`3.2`、`4.1`。章节页只列本章研究内容，不提前写结果。

结果页以图表为主体。通常一页保留一个主要分析任务、1–3 条结果描述和必要的阈值或方法注释。图过多或文字超过这一密度时，优先拆页，而不是缩小字体或堆叠说明。若同时需要讲稿，页面保留必须看到的 evidence、数字和条件，why-this-experiment、图的阅读顺序、作者解释、Critical Audit、limitation 与页间过渡优先放入 speaker notes。实际 PPTX 完成后还应检查 text overflow、shape overlap、Figure crop 和渲染后的可读性，文件能够打开不等于可交付。

可行性分析基于已经具备的理论方法、样品数据、平台条件、预实验和团队基础；进度安排区分已完成、正在进行和计划开展的工作，并使用具体任务描述未来时间段。

## 安装

从当前仓库安装：

```bash
npx skills add . --skill scientific-presentation-authoring --agent codex -g -y
```

也可以直接从 GitHub 安装：

```bash
npx skills add Akira-TL/skills --skill scientific-presentation-authoring --agent codex -g -y
```

## Runtime source

```text
productivity/scientific-presentation-authoring/SKILL.md
```
