# Analysis Execution Contract

## Reproduction entrypoint

每个进入科研 evidence 的 Analysis 至少有一个明确入口，例如：

```text
python scripts/run_analysis.py --config config/analysis.yaml
Rscript scripts/run_analysis.R config/analysis.yaml
make analysis
snakemake ...
```

入口应从已登记 input 生成已登记 output；不要依赖未记录的交互式操作。

## Environment

记录会影响结果的运行环境：语言版本、关键 package / tool 版本、外部数据库版本与必要系统依赖。优先复用项目已有 environment / lockfile，不为每个小分析新建孤立环境。

## Randomness

涉及随机初始化、重采样、交叉验证、train/test split 或 permutation 时固定 seed 或保存可重建随机状态。若结论对 seed 敏感，应把它当作 instability 结果，而不是挑选最理想 seed。

## Paths and outputs

代码使用稳定的项目相对路径、配置或明确 external URI；避免把当前机器绝对路径硬编码进分析逻辑。输出目录区分长期结果与 disposable cache。

大型 derived artifact 可以不进入 Git，但其生成入口和 provenance 必须进入项目记录。失败运行、临时 cache 和可重建中间文件不需要作为科研结果长期保存。

## Failure handling

命令失败、warning、non-convergence、missing sample 或部分输出缺失时先判断是否改变结果有效性。不得静默吞掉会改变样本、模型或结果含义的错误；只有确认无科学影响的预期 warning 才可明确处理。
