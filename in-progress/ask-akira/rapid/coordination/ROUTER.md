# Rapid Coordination Router

Rapid 只在并行或上下文切换能明显缩短关键路径时支付编排成本。

- 有两个以上互不阻塞、写入范围可以清楚隔离的工作单元 → 读取 [`parallel.md`](parallel.md)。
- 当前上下文接近边界、需要换 harness / 目录 / 人，或 side task 必须独立继续 → 读取 [`context.md`](context.md)。
- 单 Agent 可以直接完成，或任务存在严格前后依赖 → 不做编排，回到当前执行分支。

涉及 DevSpace 多 Agent、tmux 或 worktree 时使用 Akira `devspace-orchestration`；本文件只决定何时值得付这个成本。
