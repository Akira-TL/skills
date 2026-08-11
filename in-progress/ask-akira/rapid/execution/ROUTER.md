# Rapid Execution Router

Rapid execution 优先选择最小、清晰、可验证的实现路径。

- 当前修改是低风险 glue、机械适配或已有模式的直接延伸，没有复杂行为需要先锁定 → 读取 [`direct-change.md`](direct-change.md)。
- 当前切片包含关键业务行为、状态转换、复杂条件或高回归风险 → 读取 [`critical-path-testing.md`](critical-path-testing.md)。
- bug 难以定位、复现不稳定或根因不明确 → 使用 Matt `diagnosing-bugs`，不要在 Rapid 中靠猜测修。
- 测试 seam 或模块接口本身需要重新设计 → 使用 Matt `codebase-design`；设计落定后回到本 Router。

完成当前切片后进入 `../verification/ROUTER.md`。不要在实现阶段顺手扩大为架构整理；发现独立坏味道时记录并留给 Matt 标准流程。
