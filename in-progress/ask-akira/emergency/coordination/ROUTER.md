# Emergency Coordination Router

Emergency 并行的目标是缩短诊断关键路径，同时保持单一修复 ownership。

- 有多个互不依赖的只读证据源、日志面、版本区间或环境差异可以同时调查 → 读取 [`parallel-investigation.md`](parallel-investigation.md)。
- 多个 Agent 都需要写生产代码，且无法清楚隔离 ownership → 不并行写；由一个修复 Agent 保持补丁一致性。
- 需要人完成外部系统步骤 → 使用 Matt `wizard`。

需要 DevSpace 多 Agent 时使用 `devspace-orchestration`；父 Agent 统一汇总证据并裁决根因，不能用多数票替代可重复反馈环。
