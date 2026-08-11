# Competition Parallel Frontier

并行单位必须是可独立集成的价值切片，而不是“一个 Agent 做前端、一个做后端”这种长期水平分层。

- 先确认每个切片的 blocker、文件 ownership 和可独立验证结果。
- 默认并发 2～4 个；只有 frontier 天然扩大且集成成本仍低时才增加。
- 共享核心文件的写入由一个 Agent 持有，其他 Agent 通过独立模块、资产、测试、研究或 worktree 隔离。
- 子 Agent 完成后立即集成当前最高价值结果，并重跑 Demo smoke；不要等所有并行任务结束后一次性大合并。
- 截止时间逼近时停止启动回报周期超过剩余 Demo Critical Path 的新切片。
