# literature

`literature` 围绕当前 Active Uncertainty 执行文献发现、全文阅读、论文重建、批判性评估和跨论文证据综合。

默认工作模式是科研发现（Discovery），目标是找到关键方法、矛盾、边界条件和下一条判别性证据，而不是冒充系统综述。检索源按学科与任务选择，可组合 PubMed / NCBI、Europe PMC、Web of Science（WoS）、Scopus、Google Scholar、OpenAlex、Crossref、预印本与数据/代码仓库，不依赖单一检索入口。

论文机器原始件统一保存到 `.research/artifacts/papers/<paper-id>/`；XML、HTML、补充表格等不再出现在人类 `literature/` 阅读区。人类阅读区固定使用 `literature/to-read/` 与 `literature/read/`，只放按“论文题名 - 第一作者 - 年份”命名的 Markdown/PDF；主题集合用 `literature/collections/*.md` 建索引，不另造 `*_must_read/` 目录。完成阅读后的 Markdown 以三句话总结、论文逻辑、方法拆解、实验逻辑、数据直接结果、作者解释、证据评估、可复用内容、科研启发和结论边界为主线。

相关论文原则上进入全文获取与阅读流程，Observation、作者 Claim 与 Agent 的 Critical Audit 分开保存。若论文已经入库后才获得补充材料或其他新 artifact，使用 `research-db add-paper-artifacts` 追加到既有 Paper；若此前已经完成阅读，该 Paper 会重新进入增量 Reconstruction 与 Critical Audit，避免晚到附件游离在 canonical provenance 或既有审阅状态之外。

正式系统综述、范围综述和 Meta-analysis 目前不由这一普通 Discovery 流程替代。
