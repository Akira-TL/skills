# Rapid Context Boundary

上下文切换时只携带继续执行真正需要的 Work State：目标、已确认决定、当前代码状态、未完成切片、验证结果和必要产物指针。

同时携带一行规范化模式状态：

```text
Akira mode: rapid; scope: <task|session>
```

不要把“为什么一度考虑 normal / emergency / competition”的历史模式讨论写进 handoff 或 compact 摘要。新上下文重新从 `ask-akira/SKILL.md` 和 `rapid/ROUTER.md` 读取当前 Execution Policy，避免旧摘要成为规则副本。

需要跨 harness、目录或交给同事时可使用 Matt `handoff` 的产物原则；仅清空无关上下文时优先使用宿主提供的 clear / compact 能力，不为切换而制造额外文档。
