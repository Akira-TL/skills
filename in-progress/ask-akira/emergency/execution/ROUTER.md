# Emergency Execution Router

Emergency execution 只实施恢复当前 incident 所需的最小修复。

- 已有正确测试 seam，可以把最小复现直接锁成回归测试 → 读取 [`regression-first.md`](regression-first.md)。
- 没有合适 seam，或回归证据必须依赖当前反馈环 → 读取 [`minimal-patch.md`](minimal-patch.md)。
- 修复需要新增或重新设计 public seam 才能测试 → 使用 Matt `codebase-design` 判断；不要为了测试便利临时制造浅接口。

修复完成后立即进入 `../verification/ROUTER.md`。结构改善、命名整理、广泛重构和性能优化只有在它们本身就是事故根因且是恢复所必需时才进入当前 patch。
