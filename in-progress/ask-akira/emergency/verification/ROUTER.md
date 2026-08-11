# Emergency Verification Router

事故修复的完成标准是“原始故障不再发生，并且最小补丁没有制造更严重的邻接风险”。

- 需要证明 Recovery target 已恢复 → 读取 [`recovery.md`](recovery.md)。
- Recovery target 已恢复，需要检查补丁 blast radius → 读取 [`risk-review.md`](risk-review.md)。
- 修复已经扩大到普通 focused review 无法覆盖的范围 → 保持 Emergency 模式但提高验证强度；必要时使用 Matt `code-review`，不要因为模式名称继续缩减审查。

任一检查失败都回到 diagnosis 或 execution 的正确分支，不通过额外补丁堆叠绕过失败证据。
