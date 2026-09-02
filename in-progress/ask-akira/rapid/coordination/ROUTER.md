# Rapid Coordination Router

Rapid 只在并行或上下文切换能明显缩短关键路径时支付编排成本。

- 有两个以上互不阻塞的工作单元，且并行能明显缩短关键路径 → 读取 [`parallel.md`](parallel.md)。
- 当前上下文接近边界、需要换 harness / 目录 / 人，或 side task 必须独立继续 → 读取 [`context.md`](context.md)。
- 单 Agent 可以直接完成，或任务存在严格前后依赖 → 不做编排，回到当前执行分支。

本 Router 只决定是否值得并行；正式跨会话协作与当前 harness 临时并行能力的边界由 `parallel.md` 决定。
