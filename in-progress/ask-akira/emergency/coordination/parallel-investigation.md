# Emergency Parallel Investigation

把并行用于缩短“获得证据”的时间，同时保持单一生产修复 ownership。

先判断是否需要持久协作状态：

- **正式 Parallel**：调查会跨会话持续、需要多个 Worker 自主领取、调查结果会阻塞后续 Gate，或需要把一个写入型修复 Task 与多个只读调查 Task 放在同一协作图中 → 让用户进入 `/parallel-coordinator`，把当前 incident scope / tight feedback loop 作为 Source Mode Work。
- **临时调查**：父 Agent 只需要同时检查少量日志、diff、版本区间或外部状态，结果会立即回到当前会话 → 使用当前 harness 已提供的并行能力；没有对应能力时保持串行，不建立 Execution Map。

正式 Parallel 中：

- 默认只有一个写入型修复 Task 可以持有生产代码写入权；其他调查 Task 明确标记 `Task Kind: read-only`。
- 所有 Parallel Tasks 仍通过 `parallel-execution` claim；只读 Task 的 claim 保护的是调查 ownership 和 Tracker 生命周期，不授予项目写入权。
- 只读 Worker 返回可验证事实、命令/位置、证据，以及它排除或支持了什么假设；`Commit(s): none`，不得制造调查 commit。
- 写入型修复 Worker 继续当前 Emergency execution 分支，只实施恢复 incident 所需的最小 patch。
- 新证据统一回到同一个 tight feedback loop 验证。Coordinator 可以验收调查 Task，但不能因为多个 Worker 给出相同猜测就宣布根因成立。

具体 Worker 由哪一种 Agent harness、CLI、进程或终端会话执行不属于 Emergency Parallel 协议；这些实现不能拥有 claim、Task 状态、root-cause 裁决或 Gate acceptance。