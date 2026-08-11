# Emergency Minimal Patch

只修改足以让已确认根因失效、让 Recovery target 恢复的最小代码面。

执行原则：

- 优先局部修复，不趁机统一抽象、重命名邻接模块或清理历史债务。
- 不改变与事故无关的 public behavior、schema 或配置默认值。
- 每完成一个有意义的修改立即重跑 tight feedback loop，确认方向仍然正确。
- 若最小修复本身会造成新的数据、安全、权限或兼容风险，先提高验证强度，不用“Emergency”作为跳过风险处理的理由。

修复成立后停止继续优化，进入 verification。结构性后续以独立工作交还 Matt 标准流程。
