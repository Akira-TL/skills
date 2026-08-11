# Emergency Recovery Verification

按证据从近到远验证：

1. 重跑事故开始时建立的原始、未最小化反馈环，确认用户真实症状已经消失。
2. 若建立了 regression test，确认它稳定通过。
3. 运行受影响模块最相关的测试 / typecheck / build，确认补丁没有破坏直接邻接路径。
4. 清理事故调查中加入的临时 instrumentation、debug 日志和 throwaway harness；需要保留的诊断工具必须明确转成正式资产。

只有原始症状和邻接检查都成立，才能进入 risk review。
