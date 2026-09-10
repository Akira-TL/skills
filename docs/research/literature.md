# literature

`literature` 围绕当前 Active Uncertainty 执行文献发现、全文阅读、论文重建、批判性评估和跨论文证据综合。

默认工作模式是科研发现（Discovery），目标是找到关键方法、矛盾、边界条件和下一条判别性证据，而不是冒充系统综述。相关论文原则上进入全文获取与阅读流程，Observation、作者 Claim 与 Agent 的 Critical Audit 分开保存。若论文已经入库后才获得补充材料或其他新 artifact，使用 `research-db add-paper-artifacts` 追加到既有 Paper；若此前已经完成阅读，该 Paper 会重新进入增量 Reconstruction 与 Critical Audit，避免晚到附件游离在 canonical provenance 或既有审阅状态之外。

正式系统综述、范围综述和 Meta-analysis 目前不由这一普通 Discovery 流程替代。
