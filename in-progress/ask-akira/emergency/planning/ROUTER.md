# Emergency Planning Router

Emergency planning 只做 incident scope lock，不设计完整解决方案。

- 当前故障的用户可观察症状、受影响范围或恢复目标还不明确 → 读取 [`scope.md`](scope.md)。
- 这些信息已经明确 → 返回 `../ROUTER.md`，进入 diagnosis 或 execution。

不要在这里创建 feature spec、roadmap 或架构计划。事故之外的改善只记录为后续。
