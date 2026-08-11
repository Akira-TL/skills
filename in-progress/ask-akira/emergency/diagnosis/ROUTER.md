# Emergency Diagnosis Router

Diagnosis 的目标是尽快得到足够可信、可证伪的根因证据，不把事故处理变成开放式调查。

- 没有 tight、可重复、能捕捉用户真实症状的反馈环 → 使用 Matt `diagnosing-bugs` 建立并收紧反馈环。
- 已经有可靠反馈环，但根因仍有多个合理解释 → 继续使用 Matt `diagnosing-bugs` 的最小化、假设和 instrumentation 方法。
- 反馈环已经直接隔离出单一原因，或一次最小变量改变即可稳定使症状消失 / 出现 → 读取 [`direct-evidence.md`](direct-evidence.md)。

Emergency 可以在证据已经唯一时省略形式化的 3～5 个假设展示，但不能省略可重复的证据。根因足够明确后返回 `../ROUTER.md` 进入 execution。
