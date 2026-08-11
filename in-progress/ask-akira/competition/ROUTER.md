# Competition Router

Competition 的目标是在明确截止时间前最大化完整、稳定、可演示的成果。优先级由 demo / judging critical path 决定，而不是由长期架构完整度决定。

每次只选择一个当前分支并读取它；不要预读其他目录。

- 还没有明确 Demo Critical Path，或需要决定先做什么 → [`planning/ROUTER.md`](planning/ROUTER.md)
- 已经进入实现 → [`execution/ROUTER.md`](execution/ROUTER.md)
- 已经有可演示路径，需要验收和演练 → [`verification/ROUTER.md`](verification/ROUTER.md)
- 有多个独立价值切片可以并行、需要多 Agent 或上下文交接 → [`coordination/ROUTER.md`](coordination/ROUTER.md)

以下能力继续使用 Matt：

- UI 或状态模型必须先做可运行试验 → `prototype`，Competition 中优先考虑它而不是长时间纸面讨论。
- Demo 阻塞 bug 难以定位 → `diagnosing-bugs`。
- 外部 API / SDK 事实阻塞实现 → `research`。
- 人类必须完成账号、凭据、控制台配置 → `wizard`。
- merge/rebase 冲突 → `resolving-merge-conflicts`。

Competition 不主动进入 `wayfinder`、完整 spec 或完整 architecture review。若这些流程变成必要条件，说明当前比赛范围过大；优先缩小 Demo Critical Path，除非用户明确改变目标。
