# analysis

`analysis` 负责统计、生物信息学、Python/R 计算、敏感性分析和可重放分析执行。

所有 Analysis 在第一次运行结果生成代码前先登记计划并通过结果前学术语言检查。确认性 Analysis 还需要真实 Git freeze；探索性 Analysis 不伪造确认性 freeze，但同样必须先计划再执行。具体运行使用 Analysis Attempt：一次可独立审阅的参数/specification 执行由 Git commit 固定代码版本，并把 config/output/log 放在独立 `.research/analysis/<analysis>/<attempt>/` 工作目录。Attempt 不复制代码 snapshot，兄弟 Attempt/Analysis 也不能互相读取临时文件或 import 对方入口。

项目级共享 Python 实现采用 `pyproject.toml + src/<project-package>/`；具体分析入口放在 `scripts/analyses/`，通过正常 package absolute import 使用共享能力，禁止用 `sys.path` 拼路径。Analysis 输出要成为另一个 Analysis 的输入时，先提升为正式 Dataset 或 registered canonical artifact，不能直接读取上一条路线的临时 output。

默认科研计算语言是 Python：数据读取、QC、统计推断、模型、敏感性分析和供作图使用的机器可读结果表由 Python 完成。R 默认只承担 `scripts/figures/*.R` 可视化，从 Python 已生成的 plotting table 画图，不通过 `rpy2` 耦合，也不在绘图阶段重新做 sample filtering、模型拟合、显著性检验或 multiplicity correction。只有成熟关键方法主要位于 R/Bioconductor、Python 替代会降低方法学可靠性，或用户明确要求时，R 才作为正式统计分析语言并接受同等 provenance 约束。

高通量测序（Next-Generation Sequencing, NGS）的 assay-specific pipeline、reference/database、preflight、runner 与 execution provenance 由 `analysis` 调用 `ngs` 执行；统计方法、design formula、contrast、normalization、covariate、multiple-testing 与 sensitivity 的科研决定仍由 `analysis` 拥有。upstream 的自动方法选择不能替代确认性 Analysis 的结果前冻结。

若同一 Analysis 的实现优化可以由稳定机械指标衡量，可把多个 Attempt 组织成受控迭代：先固定 baseline、metric、higher/lower 方向、target 与 guard，再让每个 Attempt 只包含一个主要可解释变化；改善、未改善和失效路线都保留原因。达到机械 target 只代表这轮执行优化完成，不能自动升级 scientific Claim，也不能用外部 controller 接管科研 Git 历史。
