# Competition Parallel Frontier

并行只服务于缩短 Demo Critical Path 或提高截止时间前可交付价值，不为了形式上的多 Agent 提高并发数。

先判断是否需要持久协作状态：

- **正式 Parallel**：多个价值切片会跨会话推进、需要动态 frontier / Ownership / Gate 集成，或多个写入结果必须按共同 Demo Gate 验收 → 让用户进入 `/parallel-coordinator`。把当前 Competition Work State、Demo Critical Path 与价值切片作为 Source Mode Work，不补造 Matt Spec/Ticket。
- **临时并行**：当前父 Agent 只需要并行少量只读查找、资产处理或完全隔离的短任务，结果会立即回到当前会话 → 直接使用 `devspace-orchestration`。

进入正式 Parallel 后仍执行 Competition 策略：

- Parallel Task 以已经确认的独立价值切片为来源，不按前端 / 后端等长期水平层拆分。
- 并行度随 frontier 动态变化；只有新增 Worker 能缩短剩余 Demo Critical Path 时才扩大。
- 共享核心文件或集成热点只允许一个写入 ownership；其他 Task 通过独立模块、资产、测试、只读调查或 worktree 隔离。
- Worker 通过 `parallel-execution` 完成 claim 后，执行器才为写入 Task 建立实现 branch/worktree。
- Coordinator 完成 Task / Gate 验收后，回到 Competition verification 重跑 Demo smoke；不要把 Gate accepted 当成现场演示已经可靠。
- 截止时间逼近时停止发布回报周期超过剩余 Demo Critical Path 的新 Task，并由 Coordinator 取消或移出尚未开始的低价值工作。

`devspace-orchestration` 只负责已决定、已领取 Task 的 Agent、tmux 与 worktree 执行，不修改 frontier、blocking 或 acceptance。