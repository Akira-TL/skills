# akira-research

`akira-research` 是 Akira 科研工作流的总入口。它维护科研目标、当前主要不确定性、Research Tree、适用规范和停止边界，并按当前证据状态自主路由到文献、假设、设计、研究实施、数据、分析、解释或传播工作。

## 适合什么时候用

- 从零建立一个可持续迭代的科研项目。
- 接管已有研究目录，重新理解现有数据、分析、文献和结论。
- 只给出科研目标，让 Agent 自主判断下一条信息增益最高的工作。
- 需要长期保留 Design freeze、Study deviation、Analysis provenance、Claim boundary 和 Git 历史。

## 使用方式

这是一个用户显式启动的 Skill。通常只需要调用 `akira-research` 并给出项目路径与研究目标；后续子工作流由 Router 自主选择。项目用 `RESEARCH.md` 保存短小的当前状态，用 `.research/research.sqlite` 保存结构化科研 provenance。

## 关键边界

它不是固定阶段流水线，也不要求每个项目都经过 Hypothesis、Study 或全部子 Skill。只有存在真正的科学需要时才进入对应工作流；当下一条判别性证据必须依赖新样品、新实验、新权限或其他外部现实输入时，应在真实停止边界结束当前循环。
