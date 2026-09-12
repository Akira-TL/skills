# literature

`literature` 围绕当前 Active Uncertainty 执行文献发现、全文阅读、论文重建、批判性评估和跨论文证据综合。

默认工作模式是科研发现（Discovery），目标是找到关键方法、矛盾、边界条件和下一条判别性证据，而不是冒充系统综述。检索源按学科与任务选择，可组合 PubMed / NCBI、Europe PMC、Web of Science（WoS）、Scopus、Google Scholar、OpenAlex、Crossref、预印本与数据/代码仓库，不依赖单一检索入口。

论文机器原始件统一保存到 `.research/artifacts/papers/<paper-id>/`；XML、HTML、补充表格等不出现在人类 `literature/` 阅读区。人类阅读文件稳定放在 `literature/papers/` 根层，只保留按“论文题名 - 第一作者 - 年份”命名的 Markdown 与可选 PDF；主题/状态集合用 `literature/collections/*.md` 建索引。待读、已读、阅读优先级和 Critical Audit 状态都由数据库表达，不再通过 `to-read/read` 目录移动。

人类 Markdown 进入 Git。新生成或由 Agent 实质重写的 sidecar 使用 `akira:literature-note:v1` 固定格式：唯一一级标题写原始论文题名，文件头固定展示中文译题、第一作者、期刊/会议、年份、DOI、PMID/PMCID、Paper ID、论文类型、当前阅读用途和本地全文；正文的固定二级标题及顺序由阅读协议定义，三级及更深层标题可按论文类型展开。顶部与结尾各提供一个“我已阅读并确认当前版本”复选框，任意一个被勾选后由 `research-db sync-user-reading` 同步。文末 `akira:user-notes` 是用户专属区，Agent 只初始化边界，之后不修改、整理、总结或清空其中内容。阅读确认的 Git content OID 会把复选框状态和用户专属笔记都归一化，因此用户继续补写自己的笔记不会让已确认状态失效，而 Agent 更新自己的阅读正文仍会使旧确认自动失效。历史旧格式 sidecar 继续兼容；一旦迁入 v1，就完整遵守固定结构。用户确认与 Agent 的 Reconstruction / Critical Audit 分开，不作为 Literature completion 条件。人类 PDF 只是方便阅读的视图，默认不进入 Git。

阅读前先明确目的，再决定章节顺序：背景知识构建、前沿跟踪、方法学习、研究设计学习、证据核验和写作结构学习可以采用不同入口。研究设计与方法学习会主动追踪基础工作、代表实现、后续改进和边界条件，也允许跨领域寻找可借鉴方案，但必须比较推断单位、数据结构、测量误差、约束条件与关键假设，不能仅因表面相似就迁移方法。发表时间、被引次数、作者或期刊声望、引文网络连接度只作为发现与排序信号，不替代证据质量判断。

完成阅读后的 Markdown 固定使用三句话总结、为什么值得读、论文逻辑、方法拆解、实验逻辑、数据直接结果、作者解释、证据评估、关键图表与定位、可复用内容、科研启发、结论边界和我的笔记等二级标题。机械门禁只检查一级标题、固定书目信息字段、二级标题顺序、用户笔记边界和双确认框，不要求固定字数、实验数、图表数或启发数。它不是逐段摘要或缩短版文献综述，而是用于以后快速恢复“为什么重要、关键证据在哪里、能支持到哪里、下次该跳到哪里”。相关论文原则上进入全文获取与阅读流程，Observation、作者 Claim 与 Agent 的 Critical Audit 分开保存。若论文已经入库后才获得补充材料或其他新 artifact，使用 `research-db add-paper-artifacts` 追加到既有 Paper；若此前已经完成阅读，该 Paper 会重新进入增量 Reconstruction 与 Critical Audit，避免晚到附件游离在 canonical provenance 或既有审阅状态之外。

正式系统综述、范围综述和 Meta-analysis 目前不由这一普通 Discovery 流程替代。
