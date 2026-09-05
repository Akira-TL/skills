# analysis

`analysis` 负责统计、生物信息学、Python/R 计算、敏感性分析和可重放分析执行。

所有 Analysis 在第一次运行结果生成代码前先登记计划并通过结果前学术语言检查。确认性 Analysis 还需要真实 Git freeze；探索性 Analysis 不伪造确认性 freeze，但同样必须先计划再执行。Study/Dataset 的识别条件失效时，应 fail-closed，而不是用更复杂模型强行制造可解释性。
