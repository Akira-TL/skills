# Python Analysis

- 优先使用项目已有 Python environment 与 lockfile；新增依赖时记录版本约束与原因。
- 科研结果使用脚本 / package entrypoint 生成；Notebook 适合探索、检查和展示，不作为唯一 primary-result source。
- 随机分析显式设置并传递 random state；并行执行若破坏确定性，应记录其影响。
- DataFrame merge / join 后核对样本数、key uniqueness 与 unmatched rows；索引对齐不能靠隐式顺序假设。
- categorical reference、missing value、dtype coercion 和排序若影响模型，显式设置并检查。
- 机器学习先定义独立推断单位与 split unit，再进行 preprocessing、feature selection、tuning 与 evaluation；这些步骤必须在 validation boundary 内执行，避免 leakage。
- 保存科研结果时优先输出机器可读表 + 由代码生成的图；pickle / joblib 等模型文件只有确有复用价值时长期保存，并记录创建它的 package 版本。
