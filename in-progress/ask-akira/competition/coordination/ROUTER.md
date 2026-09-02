# Competition Coordination Router

Competition 并行只服务于缩短 Demo Critical Path 或提高可交付价值。

- 当前 frontier 有多个没有 blocking edge、且并行能缩短 Demo Critical Path 的价值切片 → 读取 [`parallel.md`](parallel.md)。
- 需要跨 Agent / harness 继续，但必须保持比赛模式和 Demo Critical Path → 读取 [`context.md`](context.md)。
- 子任务共享同一核心模块、集成顺序严格，或并行后合并成本高于节省时间 → 保持串行。

本 Router 只决定是否值得并行；正式 Parallel 的 Coordinator 负责 Task / Gate 验收，Competition verification 仍负责最终 Demo smoke。
