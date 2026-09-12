# study

`study` 记录已冻结 Research Design 的实际执行，包括稳定 Sample identity、Assay、batch/run、instrument、Sample-to-Assay 映射、protocol deviation 和执行 artifact。

它的核心边界是区分计划与现实：Design 保存计划，Study 保存实际发生的事情。缺失样品、低质量检测、处理延迟或其他偏离应作为 provenance 保留，而不是静默清洗或改写原 Design。实验现场产生的文字、图片、语音、手写记录、仪器截图和现场 log 先保留为可定位的原始实施记录，再派生结构化 Study；温度、时间、sample ID、instrument setting 等信息如果原记录不明确，就显式保留 unknown / awaiting confirmation，不能由 Agent 从上下文猜值。同一 Sample / batch 跨多个实验事件继续使用稳定 identity。

高通量测序（Next-Generation Sequencing, NGS）项目中，真实提取、建库、测序仪运行、lane/run 和偏差由 `study` 记录；BCL/FASTQ 等 raw output 交给 `data`，后续 assay-specific 计算由 `data` 或 `analysis` 调用 `ngs`。
