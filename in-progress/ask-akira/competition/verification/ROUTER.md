# Competition Verification Router

Competition verification 以“现场能稳定完成核心演示”为中心，同时保留基本工程可运行性。

- 当前切片或整条 Demo Critical Path 需要快速技术验收 → 读取 [`smoke.md`](smoke.md)。
- 技术 smoke 已通过，需要按真实演示顺序确认现场表现和 fallback → 读取 [`rehearsal.md`](rehearsal.md)。
- 发现复杂逻辑回归或难定位问题 → 回 Matt `diagnosing-bugs` / `tdd` 的对应能力，不用演示 workaround 掩盖未知根因。

每次高价值切片合入后至少重新 smoke 受影响路径；最终提交前必须跑完整 Demo Critical Path。
