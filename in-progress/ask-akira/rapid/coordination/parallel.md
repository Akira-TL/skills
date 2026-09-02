# Rapid Parallel Work

并行只用于真正独立的 frontier，不用并发掩盖未解决的依赖。

先判断是否需要持久协作状态：

- **正式 Parallel**：多个 Worker 会跨会话工作、需要动态 frontier / Ownership / Gate 验收，或写入任务之间存在后续集成关系 → 让用户进入 `/parallel-coordinator`。把当前 Rapid Work State 与切片直接作为 Source Mode Work；不要为了 Parallel 补造 Matt Spec/Ticket。
- **临时并行**：当前父 Agent 只需要同时执行少量只读调查或完全隔离、无需 Tracker 生命周期的短任务 → 使用当前 harness 已经提供的并行能力；没有对应能力时保持串行，完成后回到当前 Rapid Router。

进入正式 Parallel 后，Rapid 的执行策略仍然有效：

- 优先把当前已经确认的纵向切片映射为最少数量的 Parallel Tasks；不要为提高并发数继续细拆。
- 并行度随真实 frontier 变化，不固定 Worker 数量。
- 多个写入 Task 必须有可复核的 ownership；无法安全隔离时保持串行或使用独立 worktree。
- Worker 通过 `parallel-execution` 完成确定性 claim 后，当前 harness 才可以为该 Task 创建任务专属 branch/worktree 或开始项目写入。
- Coordinator 负责 Task / Gate 验收；具体 Agent、进程、终端会话或 worktree 如何启动属于当前 harness 的实现细节，不进入 Parallel 状态模型，也不重新拆 Task 或判定 blocker。

并发是否值得的判断标准仍是减少 Rapid 的关键路径，而不是占满 Agent 数量。