# Rapid Planning Router

Rapid planning 只消除会阻塞实现的不确定性，不把已经明确的需求重新包装成完整 spec。

- 目标、验收条件和主要约束已经明确，而且工作可以由一个 Agent 在当前执行单元内完成 → 读取 [`direct.md`](direct.md)。
- 目标明确，但需要拆成多个可独立验证的纵向切片，或存在明显依赖关系 → 读取 [`slices.md`](slices.md)。
- 仍有会改变产品行为、领域语义或不可逆架构方向的开放决策 → 使用 Matt `grilling` / `domain-modeling`；决策落定后回到本 Router。
- 必须通过可运行逻辑或可见 UI 才能判断方案 → 使用 Matt `prototype`；得到结论后回到本 Router。

不要为了获得“更正式的计划”自动进入 Matt `to-spec` / `to-tickets`。Rapid 的计划完成标准是：下一步实现已经明确，没有仍会改变当前切片方向的开放决策。
