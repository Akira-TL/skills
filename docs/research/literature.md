# literature

`literature` 围绕当前 Active Uncertainty 执行文献发现、全文阅读、论文重建、批判性评估和跨论文证据综合。

默认工作模式是科研发现（Discovery），目标是找到关键方法、矛盾、边界条件和下一条判别性证据，而不是冒充系统综述。检索源按学科与任务选择，可组合 PubMed / NCBI、Europe PMC、Web of Science（WoS）、Scopus、Google Scholar、OpenAlex、Crossref、预印本与数据/代码仓库，不依赖单一检索入口。

论文机器原始件统一保存到 `.research/artifacts/papers/<paper-id>/`；XML、HTML、补充表格等不出现在人类 `literature/` 阅读区。人类阅读文件稳定放在 `literature/papers/` 根层，只保留按“论文题名 - 第一作者 - 年份”命名的 Markdown 与可选 PDF；主题/状态集合用 `literature/collections/*.md` 建索引。待读、已读、阅读优先级和 Critical Audit 状态都由数据库表达，不再通过 `to-read/read` 目录移动。

人类 Markdown 进入 Git，并在顶部与结尾各提供一个“我已阅读并确认当前版本”复选框。两个框是同一个用户确认状态的入口：任意一个被勾选后由 `research-db sync-user-reading` 同步，并以复选框归一化后的 Git content OID 记录用户确认的正文版本。Agent 更新笔记正文后，旧版本确认自动失效；用户确认与 Agent 的 Reconstruction / Critical Audit 分开，不作为 Literature completion 条件。人类 PDF 只是方便阅读的视图，默认不进入 Git。

完成阅读后的 Markdown 以三句话总结、论文逻辑、方法拆解、实验逻辑、数据直接结果、作者解释、证据评估、可复用内容、科研启发和结论边界为主线。相关论文原则上进入全文获取与阅读流程，Observation、作者 Claim 与 Agent 的 Critical Audit 分开保存。若论文已经入库后才获得补充材料或其他新 artifact，使用 `research-db add-paper-artifacts` 追加到既有 Paper；若此前已经完成阅读，该 Paper 会重新进入增量 Reconstruction 与 Critical Audit，避免晚到附件游离在 canonical provenance 或既有审阅状态之外。

正式系统综述、范围综述和 Meta-analysis 目前不由这一普通 Discovery 流程替代。
