# Competition Context Boundary

handoff / compact 只携带继续比赛所需的 Work State：Demo Critical Path、当前 frontier、已完成切片、阻塞项、可运行命令、验证结果和必要资产指针。

同时携带：

```text
Akira mode: competition; scope: <task|session>
```

不要在摘要里复制 Competition 的完整策略，也不要保留此前考虑其他模式的讨论。新上下文重新读取 `ask-akira/SKILL.md` 与 `competition/ROUTER.md` 获取 Execution Policy。

若剩余时间或 judging criteria 发生变化，只更新 Demo Critical Path 和 frontier；模式本身仍保持 Competition，除非用户明确切换。
