# Emergency Router

Emergency 的目标是尽快恢复正确行为，同时把 blast radius 压到最低。范围扩张、顺手重构和非必要设计改进都延后到事故解除之后。

每次只选择一个当前分支并读取它；不要预读其他目录。

- 当前故障症状、影响范围或恢复目标还没有锁定 → [`planning/ROUTER.md`](planning/ROUTER.md)
- 还没有可靠复现、反馈环或根因证据 → [`diagnosis/ROUTER.md`](diagnosis/ROUTER.md)
- 根因已经足够明确，需要实施最小修复 → [`execution/ROUTER.md`](execution/ROUTER.md)
- 修复已经可验证 → [`verification/ROUTER.md`](verification/ROUTER.md)
- 可以并行调查、需要控制多个 Agent 的写入范围或需要人工操作 → [`coordination/ROUTER.md`](coordination/ROUTER.md)

以下能力继续使用 Matt：

- 建立困难 bug 的 tight feedback loop、最小化复现和根因定位 → `diagnosing-bugs`。
- merge/rebase 冲突 → `resolving-merge-conflicts`。
- 外部系统必须由人完成的步骤 → `wizard`。
- 需要查官方资料才能判断修复 → `research`。

Emergency 不自动变成架构改造项目。若事故暴露出结构性问题，先完成恢复与必要回归证据；架构改善作为后续独立工作交回 Matt 标准流程。
