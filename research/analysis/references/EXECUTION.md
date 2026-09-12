# Analysis Execution Contract

## Reproduction entrypoint

每个进入科研 evidence 的 Analysis 至少有一个明确入口。默认 Python Analysis 使用 `scripts/analyses/<analysis>.py`，R 默认使用 `scripts/figures/<figure>.R` 消费 Python 结果表，例如：

```text
uv run python scripts/analyses/altitude_effect.py --config .research/analysis/altitude-effect/A003/config.yaml
Rscript scripts/figures/altitude_effect.R analysis/altitude-effect/tables/figure-01-data.csv analysis/altitude-effect/figures/figure-01.pdf
```

入口应从已登记 input 生成已登记 output；不要依赖未记录的交互式操作。实际执行状态用 Analysis Attempt + Git commit 固定，代码版本由 Git 保存，不在 Attempt 目录复制 snapshot。

## Environment

记录会影响结果的运行环境：语言版本、关键 package / tool 版本、外部数据库版本与必要系统依赖。优先复用项目已有 environment / lockfile，不为每个小分析新建孤立环境。

## Randomness

涉及随机初始化、重采样、交叉验证、train/test split 或 permutation 时固定 seed 或保存可重建随机状态。若结论对 seed 敏感，应把它当作 instability 结果，而不是挑选最理想 seed。

## Paths and outputs

代码使用稳定的项目相对路径、配置或明确 external URI；避免把当前机器绝对路径硬编码进分析逻辑。共享 Python 实现放在 `src/<project-package>/`，科研入口放在 `scripts/analyses/`，不得依赖 `sys.path` 注入、兄弟 Analysis/Attempt 目录或未登记临时文件。Attempt 的可变 config/output/log 只写入 `.research/analysis/<analysis>/<attempt>/` 自己的工作目录。

大型 derived artifact 可以不进入 Git，但其生成入口和 provenance 必须进入项目记录。失败运行、临时 cache 和可重建中间文件不需要作为科研结果长期保存。如果某个 Analysis 输出需要成为另一个 Analysis 的输入，先提升为正式 Dataset 或其他 registered canonical artifact，不直接引用前一 Attempt 的临时 output。

## Failure handling

命令失败、warning、non-convergence、missing sample 或部分输出缺失时先判断是否改变结果有效性。不得静默吞掉会改变样本、模型或结果含义的错误；只有确认无科学影响的预期 warning 才可明确处理。
