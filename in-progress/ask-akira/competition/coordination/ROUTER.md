# Competition Coordination Router

Competition 并行只服务于缩短 Demo Critical Path 或提高可交付价值。

- 当前 frontier 有多个没有 blocking edge、写入范围可以隔离的价值切片 → 读取 [`parallel.md`](parallel.md)。
- 需要跨 Agent / harness 继续，但必须保持比赛模式和 Demo Critical Path → 读取 [`context.md`](context.md)。
- 子任务共享同一核心模块、集成顺序严格，或并行后合并成本高于节省时间 → 保持串行。

具体 DevSpace、tmux 和 worktree 编排交给 Akira `devspace-orchestration`。父 Agent 始终拥有最终集成和 Demo smoke 责任。
