# Rapid Parallel Work

并行只用于真正独立的 frontier，不用并发掩盖未解决的依赖。

- 优先并行只读调查、独立模块或互不重叠的纵向切片。
- 多个写入 Agent 必须有清楚 ownership；无法隔离时使用独立 worktree，或退回串行。
- 父 Agent 保留集成责任：读取真实输出、检查 diff、运行必要验证，不能把子 Agent 的“完成”当成证据。
- 并发数量以减少关键路径为准，不为了占满 Agent 数量继续拆分。

具体 DevSpace 编排交给 `devspace-orchestration`。
