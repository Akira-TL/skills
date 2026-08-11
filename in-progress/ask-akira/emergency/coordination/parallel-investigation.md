# Emergency Parallel Investigation

把并行用于缩短“获得证据”的时间：

- 不同 Agent 可以分别检查日志、近期 diff、版本区间、配置差异、调用路径或外部依赖状态。
- 每个调查任务必须返回可验证事实、命令 / 位置和它排除或支持了什么假设，而不是只给结论。
- 默认由一个 Agent 持有生产修复写入权；调查 Agent 保持只读，除非文件 ownership 能完全隔离。
- 新证据统一回到同一个 tight feedback loop 验证，不能因为多个 Agent 给出相同猜测就宣布根因成立。
