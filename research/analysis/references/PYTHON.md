# Python Analysis

Python 是默认科研计算与统计环境。数据读取、QC、整理、统计推断、模型、敏感性分析、显著性/multiplicity 结果和供绘图使用的正式结果表优先在 Python 中完成。

- 优先使用项目已有 Python environment 与 lockfile；新增依赖时记录版本约束与原因。
- 项目共享实现采用标准 `pyproject.toml + src/<project-package>/` layout，并通过项目环境安装自身 package；Analysis 使用正常 absolute import，不使用 `sys.path.append/insert`、临时 `PYTHONPATH` 或依赖当前工作目录的相对路径 hack。
- 具体 Analysis entrypoint 放在 `scripts/analyses/`。不同 Analysis 的 entrypoint 不互相 import；真正需要共享的逻辑先提升到 `src/<project-package>/`。
- 科研结果使用脚本 / package entrypoint 生成；Notebook 适合探索、检查和展示，不作为唯一 primary-result source。
- 随机分析显式设置并传递 random state；并行执行若破坏确定性，应记录其影响。
- DataFrame merge / join 后核对样本数、key uniqueness 与 unmatched rows；索引对齐不能靠隐式顺序假设。
- categorical reference、missing value、dtype coercion 和排序若影响模型，显式设置并检查。
- 机器学习先定义独立推断单位与 split unit，再进行 preprocessing、feature selection、tuning 与 evaluation；这些步骤必须在 validation boundary 内执行，避免 leakage。
- 保存科研结果时优先输出机器可读表。给 R 绘图的 plotting table 也属于 Python Analysis 的正式派生结果，应明确列、单位、分组和已经完成的统计量；R 不重新计算显著性、effect 或 sample inclusion。
- pickle / joblib 等模型文件只有确有复用价值时长期保存，并记录创建它的 package 版本。
