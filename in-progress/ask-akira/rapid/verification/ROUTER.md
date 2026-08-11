# Rapid Verification Router

Rapid verification 证明当前切片可交付，默认不运行与本次改动无关的大范围 ceremony。

- 需要确定本次必须运行哪些检查 → 读取 [`checks.md`](checks.md)。
- 检查已经通过，需要判断 diff 是否值得交付 → 读取 [`focused-review.md`](focused-review.md)。
- 用户明确要求正式 branch / PR review，或当前变更已经扩大到需要完整 Standards + Spec 双轴审查 → 使用 Matt `code-review`。

验证发现新的实现问题时回到 `../execution/ROUTER.md`；不要在 verification 阶段顺手展开新的功能范围。
