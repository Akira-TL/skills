# R 可视化与例外分析

R 默认是科研可视化后端，不与 Python 形成进程内耦合。常规分析链为：

```text
Python 数据/QC/统计/模型
→ 已登记机器可读结果表或 plotting table
→ Rscript
→ PDF/SVG/PNG 等图形
```

## 默认边界

- R 绘图脚本放在 `scripts/figures/`，使用 `Rscript` 独立执行；不使用 `rpy2` 把 Python/R 运行时耦合。
- R 默认只读取对应 Python Analysis 已生成并登记的结果表/plotting table，不直接重新读取 raw Dataset 建立第二套分析链。
- 为图形表示可以做 factor ordering、label、长宽表转换等不改变科研结果的表示转换。
- 绘图阶段不得重新执行 sample exclusion、normalization、model fitting、effect estimation、hypothesis test、multiple-testing correction 或 significance calculation。显著性星号、置信区间、effect、样本量等科研数值由 Python 结果表提供；R 只负责呈现。
- 手工修改图中数值、分组、显著性标记或样本显示必须回到 Python 分析/结果表或可审计绘图代码层修正。
- 图形二进制通常可重建，默认不要求进入 Git；R 脚本和其输入 plotting table 按 provenance/Git 策略保存。

## R 统计分析的例外

Python-first 不是 Python-only。只有以下情形之一成立时，R 可以承担统计/生物信息分析：

- 关键方法的成熟、权威或领域标准实现主要位于 R/Bioconductor；
- Python 替代实现会实质降低方法学可靠性或可复现性；
- 用户明确要求使用 R 完成统计分析。

此时 R 不再只是绘图脚本，而是正式 Analysis code：必须像 Python 一样保存方法、版本、参数、seed、输入输出、Git commit、Analysis Attempt 和 diagnostics provenance。Bioconductor 分析同时记录 R、Bioconductor 与关键 package/database release。

无论 R 是否承担统计分析，factor level、contrast coding、NA handling、formula 展开、join/reshape/filtering 后的独立样本数和 key mapping 都必须显式检查；并行、bootstrap、permutation、cross-validation 等随机过程固定 seed 或保存可重建随机状态。
