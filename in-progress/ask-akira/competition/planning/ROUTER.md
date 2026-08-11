# Competition Planning Router

Competition planning 只为 deadline 前的可演示价值排序，不建立长期完整 roadmap。

- 还没有一句话说清评委 / 用户最终要看到的核心结果 → 读取 [`demo-path.md`](demo-path.md)。
- Demo Critical Path 已经明确，需要安排多个交付切片和依赖 → 读取 [`slices.md`](slices.md)。
- UI 或交互方向必须看到东西才能决定 → 使用 Matt `prototype`；结论出来后回到本 Router。
- 某个外部 API / SDK 事实阻塞路径 → 使用 Matt `research`，同时继续推进不依赖它的 frontier。

计划完成标准是：最短可演示端到端路径和当前 frontier 已经明确。不要为了覆盖所有可能功能而继续扩展计划。
