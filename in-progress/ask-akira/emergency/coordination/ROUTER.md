# Emergency Coordination Router

Emergency 并行的目标是缩短诊断关键路径，同时保持单一修复 ownership。

- 有多个互不依赖的只读证据源、日志面、版本区间或环境差异可以同时调查 → 读取 [`parallel-investigation.md`](parallel-investigation.md)，由该分支判断是否需要正式 Parallel 状态。
- 多个 Agent 都需要写生产代码，且无法清楚隔离 ownership → 不并行写；由一个修复 Agent 保持补丁一致性。
- 需要人完成外部系统步骤 → 使用 Matt `wizard`。

Emergency 始终保持单一修复 ownership；正式 Parallel 只增加协作状态，不改变这一点。根因仍由可重复反馈环裁决，不能用多数票替代证据。
