# Rapid Critical-path Testing

对真正决定当前切片是否正确的行为使用测试驱动，但不要求每个低风险胶水改动都进入完整 Matt TDD ceremony。

1. 优先选择项目已经存在的最高 public seam。若 seam 明显，说明选择后直接继续，不额外等待一次确认。
2. 先让一个能够捕捉当前关键行为的测试变红，再写最少实现让它变绿。
3. 一次只推进一个行为切片；不要预写整组未来测试。
4. seam 本身存在多个有意义设计方案、需要新增 public interface，或测试只能依赖内部实现时，停止本文件并使用 Matt `codebase-design` / `tdd` 的完整方法。

Rapid 的裁剪点是减少低价值 ceremony，不是降低测试可信度。测试仍然验证外部行为，expected value 仍应来自独立事实而不是复算实现。
