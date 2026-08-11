# Competition Execution Router

Competition execution 先保证端到端存在，再逐步提高价值和完成度。

- Demo Critical Path 还没有真实跑通 → 读取 [`skeleton.md`](skeleton.md)。
- Skeleton 已经跑通，需要实现当前最高价值切片 → 读取 [`value-slice.md`](value-slice.md)。
- UI / 交互方向需要快速比较多个方案 → 使用 Matt `prototype`。
- Demo 阻塞 bug 无法快速定位 → 使用 Matt `diagnosing-bugs`；不要靠叠 workaround 猜原因。
- 当前行为属于复杂关键逻辑，错误会直接破坏核心演示 → 可使用 Matt `tdd` 或在已有 seam 上写最小 critical-path test。

每完成一个可独立演示的切片就返回 planning / verification 重新判断 frontier，不批量完成所有功能后才第一次集成。
