# 科研论文 Figure 工作流

本文件用于原始研究论文、综述及其他正式科研传播中的 publication figure / multi-panel figure。Figure 是科学证据的可视化组织，不是独立于科研论证的装饰。数据分析、统计量与正式 plotting table 仍由 `analysis` 负责；本文件负责 panel 组合、证据结构、图注边界、版式与交付前视觉审查。

## 1. 先确定 Figure 回答什么，再开始排版

开始画图或组 panel 前，先写清：

```text
Results-level scientific question
Figure-level Claim
哪一种结果会推翻或明显限定这个 Claim
最关键的 evidence 是什么
每个 panel 分别承担什么作用
```

Figure 的规划单位是科学问题和 Claim，不是“现有几个 CSV / 几种 metric / 几张图片”。不要因为已经有四个结果文件，就机械做成 a–d 四个 panel。

一个 Figure 默认围绕一个主要科学判断组织；可以包含多个从属发现，但它们应共同建立、限定、检验或解释同一个更高层 Claim。若某个 panel 实际承担另一个独立主要结论，应考虑形成另一个 Figure 或 Results 单元。

## 2. 多面板图中的 panel 要承担不同证据作用

根据当前研究实际需要选择最小充分 panel 集。常见作用包括：

- 研究系统、实验设计、流程或比较关系说明；
- 代表性实例，用于让读者理解现象具体长什么样；
- 主要定量证据；
- baseline / control / comparator；
- 分解或分层，说明效应来自哪些组成或在哪些条件下成立；
- 独立测量、正交方法或外部数据验证；
- perturbation / stress test，用于检验关键解释；
- 失败案例或适用边界；
- 在证据允许时展示机制层证据。

不要用“不同 metric”冒充“不同证据作用”。两个 panel 如果只是同一结论换一个指标或画法，而没有增加新的推断信息，优先合并、移入 Supplement，或删除重复展示。

对每个主要 panel 至少能回答：

| 项目 | 问题 |
| --- | --- |
| Scientific question | 这个 panel 独立回答什么 |
| Evidence role | 它建立、比较、验证、排除、限定还是解释什么 |
| Decisive comparison | 读者真正需要看的比较是什么 |
| Unique inference | 去掉它以后会损失什么推断 |
| Claim dependency | 它支持 Figure-level Claim 的哪一步 |
| Destination | Main Figure / Supplement / another Figure |

如果遮住一个 panel 后 Figure 的科学论证完全不受影响，该 panel 默认不应占据主图空间。

## 3. Figure 内部和 Figure 之间都要形成科学推进

多面板图不应像 dashboard 一样并列堆结果。panel 顺序应让读者理解：

```text
建立现象
→ 与合理替代解释或 baseline 比较
→ 做关键 discriminator / robustness / orthogonal validation
→ 明确 generalization 或 failure boundary
→ 在证据允许时形成更深解释
```

不要求每张图都包含所有步骤，只保留当前 Claim 真正需要的部分。

整篇论文的 Figure 顺序也应和 Results 的问题推进一致。后一张 Figure 应回答前一张结果自然产生的新问题，而不是连续多张图都只重复“X 表现较好”。若两个 Figure 可以用同一句结论概括，应重新检查是否需要合并、降级次要证据或让后一张 Figure 解决更深的 uncertainty。

## 4. Main Figure、Supplement 与正文材料分配

Figure 分配继续遵守“材料完整、正文聚焦”的原则：

- **Main Figure**：主要证据、必要 control、关键 falsification、会改变主要解释的边界；
- **Supplement / Extended Data**：不改变中心结论的 secondary metric、alternative estimator、扩展 subgroup、额外 robustness、实现和 provenance 细节；
- **另一个 Figure**：独立的主要科学问题或下一层 Claim；
- **合并 / 删除重复视图**：没有额外推断价值的重复图形。

负结果、failure case 或 boundary 只要会改变主要 Claim 的方向、大小、范围或可信度，就不能因为影响版面或故事完整性被埋到 Supplement。

## 5. Figure 设计必须保持数据与统计含义

Publication layout 不得改变 Analysis 的科研含义：

- 不为适配模板静默删除 sample、replicate、category 或 time point；
- 任何实际排除都必须回到 canonical Data / Analysis 规则并保留 before/after count、规则和原因；
- matched / paired design 的主要 Claim 若依赖配对差异，不能只画容易掩盖配对效应的 marginal distribution；
- comparable panels 的 `n`、denominator、estimator、uncertainty、scale、normalization 和 comparator 必须保持一致，或明确标出差异；
- 显著性标记、`P` 值、置信区间和 multiplicity adjustment 只能来自已登记的 Analysis result；
- schematic / graphical model 不能把 plausible mechanism 画成已经证实的机制链。

## 6. 视觉层级服从证据层级

Figure 的视觉注意力应该优先落到决定性证据，而不是颜色最亮、图形最复杂或最容易宣传的 panel。

- 关键 quantitative evidence 应获得足够空间；
- control / robustness panel 可以视觉上次要，但必须仍可判断；
- 相同 group / condition / method 在不同 panel 使用一致 mapping；
- 不强迫不同科学作用的 panel 等面积；
- setup schematic 只有在帮助解释后续 evidence 时才放入，不机械把 `a` panel 做成示意图；
- 会改变结论的 negative result / failure boundary 必须视觉可见；
- 颜色、marker、line style 等编码不能让次要 baseline 比主要证据更突出。

## 7. Figure legend 负责“怎么读图”，正文负责“结果意味着什么”

Legend 至少应让读者无需猜测就知道：

- panel 展示什么对象、条件和比较；
- `n` 的定义与独立实验单位；
- center / spread / interval 的含义；
- statistical test 与 correction（若适用）；
- 关键 symbol、color、line、scale bar、normalization；
- source data / analysis output 的对应关系。

正文不重复朗读图中所有数字；它负责指出关键 Observation、科学意义以及为什么这项结果引出下一步。Legend 也不承担完整 Discussion。

## 8. 最终 Figure 必须按实际输出尺寸逐 panel 审查

不能只看绘图源码或缩略图。正式交付前，对最终 SVG/PDF/TIFF/PNG 或目标格式在实际物理尺寸下逐 panel 检查，再看整图：

- 标签、tick、legend、注释是否可读且无重叠 / clipping；
- comparable panels 的轴、单位、scale、颜色和 uncertainty 定义是否一致；
- panel label 和阅读顺序是否清楚；
- 关键数据点、error bar、scale bar、image annotation 是否被遮挡；
- grayscale / color-vision 条件下是否仍能区分关键类别；
- vector text 是否按目标期刊要求保留可编辑性；
- raster / microscopy / photograph 是否有足够分辨率与正确 scale calibration；
- image crop、contrast、pseudo-color、stitching 等处理是否有 provenance；
- 每一个 quantitative panel 是否可回到 canonical plotting table / source data / Analysis artifact。

自动化 collision、alignment、font-size 或 export check 可以作为机械 QA，但不能替代逐 panel 科学审查。具体尺寸、字体、格式、颜色模式和投稿阶段要求应通过 `research-standards` 查询**当前目标期刊**的正式规则，不把某个 Nature journal 的固定数值推广成 Akira 通用标准。

## 9. 绘图实现继承 Analysis 的语言边界

Akira 默认科研计算仍由 Python 完成，R 默认消费冻结后的 plotting table 完成 publication visualization。Figure 组合和传播设计属于 Communication，但不重新在绘图脚本中做 sample filtering、normalization、model fitting、effect estimation、显著性检验或 multiplicity correction。

若成熟关键可视化实现主要存在于 Python、目标工具链明确要求 Python，或用户明确指定其他实现，可以按 `analysis` 的既有例外规则执行；不要为了套用第三方 Figure Skill 再引入第二套 Python/R backend 选择协议。

## 10. Figure 完成检查

交付前至少确认：

1. Figure-level scientific question 和最窄 Claim 明确；
2. 每个 panel 有独立证据作用，没有纯 metric duplication；
3. panel 顺序和 Figure 顺序与 Results 的科学推进一致；
4. conclusion-changing negative evidence / boundary 没有被隐藏；
5. Figure / legend / main text 的 `n`、统计量、单位与 uncertainty 一致；
6. 每个 quantitative panel 能回到 canonical Analysis output；
7. image processing 有必要 provenance；
8. 最终实际尺寸逐 panel QA 已完成；
9. target journal 的当前 Figure / legend / source-data 规范已核验。
