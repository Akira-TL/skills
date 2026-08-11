# Competition Smoke Verification

按真实演示路径做最小技术验收：

1. 项目能从约定脚本正常启动 / 构建。
2. Demo Critical Path 从入口走到核心结果。
3. 当前关键输入和最可能现场使用的输入不会产生 runtime error。
4. 外部依赖失败时，已设计的 fallback 可以实际触发。
5. 改动涉及类型或编译边界时运行对应 typecheck / build；关键逻辑有测试时运行相关测试。
6. 检查 diff 中没有凭据、临时 debug、明显硬编码的本机路径或只能在开发者机器成立的假设。

Smoke 失败时优先修复阻塞 Demo 的最高风险项，再重新从路径入口运行，而不是只重试失败的最后一步。
