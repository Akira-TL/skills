# R Analysis

- 优先使用项目已有 R environment、`renv` 或其他既有版本记录；新增 package 时记录版本与来源。
- 关键结果由 `.R` 脚本、Quarto/R Markdown 的可重建执行或 workflow 生成；交互式 Console 操作不能成为唯一 provenance。
- factor level、contrast coding、NA handling、formula 展开和 group ordering 会改变模型时显式设置并核对。
- join / reshape / filtering 后核对独立样本数与 key mapping，避免因 tibble/data.frame 行顺序或重复 key 静默改变 biological `n`。
- Bioconductor 分析同时记录 R、Bioconductor 与关键 package 版本；涉及 annotation / organism database 时记录对应 release。
- 并行、bootstrap、permutation、cross-validation 等随机过程固定 seed 或保存可重建随机状态。
- 绘图从已登记结果表生成；手工修改图中数值、分组、显著性标记或样本显示必须回到代码/数据层修正。
