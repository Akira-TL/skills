# 模糊科研想法的收敛协议

本文件用于用户只有宽泛兴趣、现象描述、方法兴趣或一句模糊科研想法，而尚不足以建立可判别 Research Question / Active Uncertainty 的情况。它不是新的科研阶段，也不是问卷模板；目标是用最少但真正改变问题定义的交互，把模糊 Idea 收敛成可进入 Research Tree 的科学对象。

## 1. 先判断缺的是科学问题，不是措辞

不要把一句宽泛主题直接改写成“漂亮题目”后当作 Research Question。例如“研究高原牦牛肠道菌群适应”仍可能同时包含描述差异、解释机制、预测 phenotype、验证因果或寻找干预靶点等完全不同的问题。

先区分当前缺口：

- 科学对象不清：研究的是哪个 population / system / exposure / phenotype / process；
- 目标不清：要描述、解释、预测、比较、验证机制还是评价干预；
- outcome / measurement 不清：真正关心的可观测对象是什么；
- uncertainty 不清：当前哪两个或多个 plausible states / explanations 尚不能区分；
- scope 不清：什么时间、空间、群体、条件、数据或资源边界真实存在；
- decision relevance 不清：不同答案会不会改变后续研究路线。

若只是标题措辞不佳而科学问题已经明确，不启动本协议。

## 2. 只追问会改变路线的问题

优先利用项目已有 evidence、用户已经给出的上下文和可低成本核验的资料。不要一次抛出十几项表格式问题，也不要重复询问已经知道的事实。

一轮追问通常只聚焦当前最阻塞的 1–3 个维度，例如：

1. **研究对象**：真正希望解释或改变的对象是什么？
2. **科学目标**：如果研究成功，用户最希望能多知道哪一种事实——现象、效应、机制、预测还是干预效果？
3. **关键未知**：现在最重要的“不知道”是什么，而不是“还想多了解什么”？
4. **竞争状态 / 解释**：至少有哪些当前 evidence 尚未排除的可能世界？
5. **判别证据**：什么观察、分析或实验结果会让这些可能性得到不同更新？
6. **现实边界**：现有样本、数据、平台、时间、伦理或权限会排除哪些问题写法？

如果用户给出的答案仍然只是工作流目标（如“想做得更深入”“想发高水平论文”），继续追到科学对象与可判别 uncertainty；这些目标可以作为战略约束，但不能替代 Research Question。

## 3. Literature 可以帮助定义问题，但不能替用户造目标

当用户连领域中的稳定现象、主要术语、已知争议或可行 measurement 都不清楚时，可以先进行低成本 Literature Discovery，用于：

- 建立术语和对象边界；
- 识别领域已经回答的问题；
- 找到真实 contradiction / boundary / methodological limitation；
- 判断某个初始 Idea 是否已经被充分回答；
- 找到可产生不同预测的 competing explanations。

文献用于缩小科学问题空间，不用于从热门论文中自动挑一个“看起来能发”的题目。若检索产生多个价值取向明显不同的研究方向，再按 `RESEARCH-COLLABORATION.md` 向用户呈现真正的战略分叉。

## 4. 收敛输出

只有信息足够时才把 Idea 固化为 Research Tree 对象。最低应能形成：

```text
Objective: <项目总体想理解、解释或解决什么>

Research Question: <一个可以由证据推进的科学问题>

Active Uncertainty:
  Competing explanations / states:
  - <E1>
  - <E2>

  Discriminating gap: <当前证据为什么区分不了>
  Best next evidence: <最能改变判断的一条现实可得证据>

Open Threads:
- <重要但当前不作为 primary 的其他问题>
```

若暂时只能形成 Objective，而还不能形成可判别 Research Question，就如实保持在 `EXPLORE / QUESTION`，继续补最小必要 evidence；不要用模型自信填满空白。

## 5. 用户与 Agent 的来源边界

- 用户原始 Idea、研究偏好和现实约束保留用户来源，不改写成 Agent 自己提出；
- Agent 生成的新 competing explanation / hypothesis 若值得持续追踪，按科研协作协议记录 `origin=agent`；
- 用户选择“更想做机制”“更重视预测”“只允许使用已有数据”等属于 research priority / strategic preference / resource constraint，不等于对应 Hypothesis 已获 evidence 支持；
- 用户明确授权 Agent 在某个范围自主收敛问题后，可以继续低成本探索，不机械逐项征求批准，但改变 Objective、主要问题或进入明显新资源前仍按协作边界呈现。

## 6. 停止 Socratic 追问

当已经能够写出单一 Research Question、至少两个可区分状态或清楚说明为什么当前还不能形成 competing explanations，并能指出现实的 Best next evidence 时停止追问，进入实际 Literature / Hypothesis / Design / Analysis 动作。

不要把“继续讨论问题本身”当成无限阶段。问题已经足够可行动时，下一步应该取得 evidence。