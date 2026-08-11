# Competition Value Slices

围绕 Demo Critical Path 拆纵向价值切片，并按“演示价值 ÷ 完成风险”排序。

优先顺序：

1. **Skeleton**：一条最小端到端路径能够跑通，即使内容粗糙。
2. **Core value**：让核心结果真正有说服力的功能。
3. **Reliability**：消除最可能让现场演示失败的问题和外部依赖单点。
4. **Presentation**：直接提高理解速度、视觉完成度或 judging criteria 命中率的改进。
5. **Optional**：只有前四类稳定后才进入。

每个切片声明 blocker。没有 blocker 的高价值切片进入当前 frontier；不要为了形成正式 tickets 再等待一轮审批。
