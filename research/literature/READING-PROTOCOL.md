# 论文阅读与人类文献区契约

本文件定义 `literature` Skill 的单篇论文阅读顺序，以及科研项目中机器论文 artifact 与人类阅读文件的目录边界。结构化科研事实仍以 `research.sqlite` 与原始 artifact 为准；本文件只规定如何读、如何给人看、文件放在哪里。

## 1. 机器归档与人类阅读区必须分离

论文原始来源统一进入机器归档：

```text
.research/
└── artifacts/
    └── papers/
        └── P000001/
            ├── paper.xml
            ├── paper.pdf
            ├── supplementary-methods.pdf
            └── source-data.xlsx
```

这里可以保存 PDF、XML、HTML、表格、补充材料、代码/数据附件等真实来源表示。它用于 Agent、数据库 provenance 与审计，不是用户日常浏览论文的入口。

`literature/` 只作为人类阅读区：

```text
literature/
├── README.md                 # 可选，总索引
├── to-read/                  # 已筛选、等待完整阅读
│   ├── <题名> - <第一作者> - <年份>.md
│   └── <题名> - <第一作者> - <年份>.pdf
├── read/                     # 已完成 Reconstruction + Critical Audit
│   ├── <题名> - <第一作者> - <年份>.md
│   └── <题名> - <第一作者> - <年份>.pdf
└── collections/              # 可选，仅放主题索引 Markdown
    └── <主题>.md
```

约束：

- `to-read/` 与 `read/` 保持平铺，不再建立 `P000001/`、`Dprime_must_read/`、`important/` 等临时层级。
- `to-read/` 与 `read/` 只出现 `.md` 与 `.pdf`；XML、HTML、JSON、CSV、XLSX、图片、补充附件和其他机器 artifact 留在 `.research/artifacts/papers/`。
- `collections/` 只保存 Markdown 索引，通过链接组织“必读”“方法学”“某研究问题”等集合，不复制论文或另造一套状态目录。
- 人类文件的基础名采用 `<论文题名> - <第一作者> - <年份>`。只对文件系统非法字符做必要替换；不要用 Paper ID、内部缩写或 Agent 自造主题名替代书目信息。
- Paper ID、DOI、PMID 等稳定身份写在 Markdown 内，不要求用户从文件名记忆数据库 ID。
- 人类 PDF 是方便阅读的视图，不是新的 scientific source。已有合法 PDF 表示时可复制或链接到人类区；如果当前合法全文只有 XML/HTML，不把 XML/HTML 暴露到 `literature/`，而是在 Markdown 中说明当前没有可供人直接阅读的 PDF，并继续按 `literature-access` 检查合法 PDF 路径。
- 历史项目原有 `literature/papers/` 只作为 legacy 兼容来源；新 artifact 不再写入该目录，也不在其上继续扩展人类阅读结构。

完成 Critical Audit 时，最终 Markdown 必须位于 `literature/read/` 并作为 `papers.sidecar_path` 关联。尚在阅读队列中的 Markdown/PDF 位于 `literature/to-read/`；阅读完成后把对应人类视图移动到 `read/`，机器 canonical artifact 不移动。

## 2. 先判断是否值得投入阅读

Candidate 完成 identity resolution 后，先用标题、摘要、关键词、论文类型、主要方法/数据和当前 Active Uncertainty 做价值筛选。重点判断：

- 是否直接回答或约束当前 Research Question / Active Uncertainty；
- 是否提供能区分 competing explanations 的证据；
- 是否包含领域经典模型、关键方法、重要 protocol 或后续工作反复依赖的基础结果；
- 是否提供当前项目可复用的代码、数据、模型、参数或实验设计；
- 是否属于足以改变当前判断的近期研究；
- 是否与现有证据冲突，因而值得优先核验；
- 是否只是关键词命中而实际不属于问题空间。

这些判断映射到既有 `reading_priority = core | high | normal | low` 与 `relevance_status`，不建立另一套“必读”等状态字段。

摘要只用于导航和优先级判断。摘要难以理解不等于论文应排除：先区分“论文确实无关”与“缺少术语、方法或基础背景”。高度相关但难懂的论文保留 Candidate，并先追 prerequisite、术语或 foundational work 后再回来阅读。

## 3. 快速阅读：先重建论文为什么存在

快速阅读不是逐句读全文。目标是回答：这篇论文值不值得继续投入，以及作者的论证主线是什么。

优先检查标题、摘要、引言、主要图表、结论/讨论，并形成下面的逻辑链：

```text
以前怎么做
→ 以前的方法为什么不足
→ 作者真正要解决什么问题
→ 作者提出什么核心思路
→ 为什么这个思路理论上可能解决问题
→ 哪些实验承担关键验证
```

如果快速阅读后仍无法说清研究问题、核心思路和最关键实验，就不能把论文当作已经读懂；根据相关性决定补背景还是降低优先级。

## 4. 精读：方法按“输入—过程—输出”拆解

方法部分优先回答动作，而不是逐句翻译正文或公式。

至少重建：

```text
研究对象 / Input
→ 关键操作、模型结构或实验过程
→ 关键参数、假设与中间表示
→ Output / Measurement
→ 这些输出如何回答 Research Question
```

遇到公式时，先解释公式在方法链中执行什么动作，例如定义目标函数、估计效应、计算相似度、归一化、更新参数或实施统计检验。只有公式细节会改变方法理解、复现或证据判断时，才继续推导符号和数学细节。

对生物实验、组学和计算流程同样按可追踪步骤表达，例如：样本 → 前处理 → 测量/测序 → QC → 特征构建 → 统计模型 → 目标结果。关键软件、数据库版本、参数、阈值、随机种子和 protocol 仍按 `DEEP_EXTRACTION` 要求进入结构化 Method provenance。

## 5. 实验按“为什么做—怎么做—得到什么”阅读

每个关键 Experiment 都回答：

1. 这个实验想检验什么问题或论证步骤；
2. 为什么需要这个实验；
3. 使用什么样本、组别、对照、变量与分析；
4. 数据直接显示什么；
5. 该结果能够支撑作者哪一级 Claim；
6. 是否还有替代解释；
7. 实验设置是否报告到足以复现。

不同实验类型尤其关注：

- 对比实验：作者的方法相对于已有方法是否真的改善，比较条件是否公平；
- 消融实验（Ablation Study）：性能或现象究竟来自哪个模块、变量或设计决策；
- 鲁棒性/外部验证：是在扩大适用范围、检验稳定性还是排除替代解释；
- 机制实验：是否真正测试机制链，还是只提供与机制一致的间接证据。

这层人类理解必须继续映射到数据库的 Method、Experiment、Observation、Claim 与 relation；不能用阅读笔记替代结构化 provenance。

## 6. 与两遍阅读协议的关系

快速阅读与上述方法/实验拆解是阅读策略，不替代 `SKILL.md` 的两遍科研审阅：

- Pass 1 Reconstruction：忠实重建 Method / Experiment / Observation / Claim / Lead，并保留精确 source locator；
- Pass 2 Critical Audit：以审稿人/竞争课题组视角检查设计、统计、可复现性、证据跳跃、替代解释与边界。

Observation、作者 Claim 与 Agent 科研判断始终分开。人类笔记可以把它们组织得更易读，但不得把三个层级压成一句“论文证明了……”。

## 7. 人类 Markdown 的固定阅读结构

完成阅读后，`literature/read/<题名> - <第一作者> - <年份>.md` 至少使用以下顺序；不要求机械填满没有内容的栏目，但不得省略会影响理解或证据边界的部分。

```text
# 论文题名

书目信息

## 三句话总结
1. 这篇论文解决什么问题。
2. 它怎么解决。
3. 最重要的实验结果及结论边界是什么。

## 为什么值得读
- 与当前项目 / Active Uncertainty 的关系
- 为什么被列为当前阅读优先级

## 论文逻辑
- 以前怎么做
- 以前为什么不够
- 作者要解决什么
- 核心思路

## 方法拆解
- 输入
- 核心过程
- 输出
- 关键公式/模型在做什么
- 关键参数与复现信息

## 实验逻辑
- 每个关键实验为什么做
- 对比实验
- 消融实验
- 其他验证
- 是否足以复现

## 数据直接显示什么

## 作者如何解释

## 我们的证据评估
- 直接支持什么
- 间接支持/限定什么
- 没有建立什么
- 主要问题与替代解释

## 可复用内容
- 方法 / protocol
- 代码 / 数据
- 参数 / 模型

## 科研启发
- 这篇论文改变了我们什么认识
- 产生了什么新 Research Question / Hypothesis / Analysis / Design 线索

## 结论边界
```

“三句话总结”是用户恢复论文的入口，不替代后文证据层级。科研启发属于 Agent/项目产生的新判断，不得伪装成作者结论；值得持续追踪的启发继续按项目 provenance 写入 Lead、Research Question、Hypothesis Proposal 或 Research Tree。
