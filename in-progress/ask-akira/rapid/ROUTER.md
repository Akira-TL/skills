# Rapid Router

Rapid 的目标是用最少 ceremony 尽快交付仍可维护的软件。当前模式只改变流程成本，不降低已经识别出的风险。

每次只选择一个当前分支并读取它；不要预读其他目录。

- 需求已经清楚，需要决定是否直接开始或如何切片 → [`planning/ROUTER.md`](planning/ROUTER.md)
- 已经可以写代码 → [`execution/ROUTER.md`](execution/ROUTER.md)
- 实现已经达到可验证状态 → [`verification/ROUTER.md`](verification/ROUTER.md)
- 存在可以安全并行的独立工作、需要跨上下文继续，或需要控制 HITL 成本 → [`coordination/ROUTER.md`](coordination/ROUTER.md)

以下情况直接使用 Matt 的标准能力，不在 Rapid 内复制：

- 真正阻塞实现的产品/领域决策 → `grilling`，必要时配合 `domain-modeling`。
- 必须运行或看到结果才能决定设计 → `prototype`。
- 难以定位、间歇性或回归型 bug → `diagnosing-bugs`。
- seam 或模块接口本身需要设计 → `codebase-design`。
- merge/rebase 已经冲突 → `resolving-merge-conflicts`。
- 外部资料事实阻塞实现 → `research`。

若工作已经巨大到无法在当前执行单元内看清主要路径，不要把 Rapid 逐步膨胀成 Matt 的完整规划流程；向用户说明当前任务已经超出 Rapid 的适用边界，并继续保持当前模式，直到用户明确切换或缩小范围。
