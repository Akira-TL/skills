# Analysis Attempt 与执行隔离契约

Analysis 回答一个可独立解释的科研问题；Analysis Attempt 表示该 Analysis 下的一次具体、可重放执行状态。二者不能混成“每调一个参数就新建 Analysis”，也不能把所有试错堆在同一工作目录里互相调用。

## 1. Attempt 何时创建

同一 scientific question / estimand / population / unit of inference 下，以下变化通常建立新的 Attempt，而不是新的 Analysis：

- 参数或配置改变；
- seed / split 改变；
- 同一方法的合理 specification；
- 诊断后调整但仍回答同一科研问题；
- 实现细节或性能优化会影响可重放执行状态。

语法错误、路径错误、依赖未安装等程序根本没有形成有效科研执行的失败，不必机械登记成正式 Attempt。

当 scientific question、estimand、population、unit of inference、confirmatory target 或解释目标实质改变时，建立新的 Analysis / Research Tree branch。

## 2. Git 固定代码，Attempt 不复制代码快照

代码版本由 Git 保存。Attempt 至少记录：

```text
analysis
attempt_key
parent_attempt（可选，仅表示历史来源）
status
reason
git_commit
config_path
output_path
decision_reason（selected 时）
started_at / completed_at
```

`git_commit` 表示该次执行实际使用的代码状态；不要在 `.research/analysis/...` 再复制一套 `code_snapshot/`。已登记到 Attempt 的 commit 不得被 rebase/reset/amend 重写。

Attempt key 使用 `A001`、`A002`、`B001` 这类“大写字母 + 至少三位数字”。它只是 Analysis 内部执行身份，不进入 Git branch 名。

## 3. 每个 Attempt 有独立工作目录

机器执行状态统一位于：

```text
.research/analysis/<analysis-slug>/<attempt-key>/
```

其中可以出现：

```text
config.yaml
outputs/
logs/
```

`config_path` 与 `output_path` 必须位于当前 Attempt 自己的目录。兄弟 Attempt 之间不得共用可变工作文件。

`.research/analysis/**/outputs/` 与 `logs/` 默认 Git ignore；真正进入科研 evidence 的小型 canonical result 应提升到该 Analysis 的人类/canonical result area 并按 `analysis_artifacts` 登记，而不是依赖临时输出目录长期存在。

## 4. Analysis 之间默认运行时隔离

任何 Analysis / Attempt 都不得直接读取、import、source 或调用其他 Analysis / sibling Attempt 的代码、配置、中间结果或临时文件。尤其禁止：

```text
analysis/<other-analysis>/...
.research/analysis/<other-analysis>/...
scripts/analyses/<other-entrypoint> 作为 Python import source
sys.path.append / sys.path.insert 等动态路径注入
```

从旧 Attempt / Analysis 复制代码作为新路线的起点是允许的，但复制完成后两边成为独立 Git 内容；`parent_attempt` / Research Tree relation 只记录 provenance，不形成运行时依赖。

## 5. 共享代码必须提升到项目 package

真正稳定、需要跨 Analysis 复用的 Python 实现进入：

```text
src/<project_package>/
```

项目使用标准 `pyproject.toml` / `src` layout，并在项目环境中安装自身 package。Analysis entrypoint 使用正常绝对 package import：

```python
from project_package.statistics import fit_model
```

不得靠当前工作目录、`../`、`PYTHONPATH` 临时拼接或 `sys.path` hack 维持 import。

具体科研入口放在：

```text
scripts/analyses/<analysis>.py
```

`src/` 表示稳定可复用能力，`scripts/analyses/` 表示具体 Analysis 的执行入口。某 Analysis 的临时 helper 如果还不具备项目级复用语义，可以先留在该入口附近，但不能通过另一个 Analysis 的入口间接复用；真正共享时先重构进 `src/`。

## 6. 下游输入只能来自 canonical Dataset / registered artifact

Analysis B 不得直接读取 Analysis A 的 Attempt 临时输出。如果 A 的输出确实成为后续科研对象，应先显式提升并登记为 Dataset 或其他稳定 canonical artifact，再由 B 作为正式输入使用：

```text
Dataset D1 → Analysis A → promoted Dataset D2 → Analysis B
```

而不是：

```text
Analysis A/tmp/foo.csv → Analysis B
```

这条边界用于阻断隐式 provenance 链和“删掉 A 就无法复现 B”的污染。

## 7. 可量化目标下的受控迭代

当同一 Analysis 的改进目标可以用**稳定、可重复测量的机械指标**表达时，可以把一组 Attempt 组织成受控迭代。适用例子包括：运行时间、内存、预测误差、交叉验证评分、测试失败数、覆盖率、收敛诊断或其他项目已经定义且与科研目标一致的量化指标。

这种模式只用于**执行或实现优化**，不能把“某个数字更好”自动等同于 scientific validity。开始迭代前先在 Analysis plan / config 中固定：

```text
baseline
metric
优化方向（higher / lower）
target（若存在明确完成阈值）
verification command / procedure
guard（必须保持成立的科学或工程约束）
```

要求：

1. baseline 与 guard 必须在第一次改动前真实运行；
2. metric 自身若噪声过大、不可重复或容易被实现副作用污染，先修测量方法，不把随机波动解释成进步；
3. 每个 Attempt 只包含一个可解释的主要变化；若同时改动多个独立因素导致无法归因，应拆成多个 Attempt；
4. Attempt 的结果必须同时报告 metric 与 guard，不能只保存“最好的一次”；
5. metric 改善但违反统计前提、数据边界、leakage 规则、科学约束或 guard 时，该 Attempt 不得 selected；
6. metric 未改善但形成了有效执行时保留为 `abandoned` 并写明原因；违反方法、数据或实现前提时使用 `invalid`；
7. 达到 target 只表示这轮机械优化目标完成，不自动升级 scientific Claim，也不跳过后续 diagnostics / sensitivity / Interpretation。

Akira 不允许第三方优化 controller 接管科研 branch 的 Git 生命周期。每个进入科研 provenance 的 Attempt 仍由 Akira 正常提交并记录；失败路线通过新的状态/提交保留审计历史，不对已登记 commit 做 reset / amend / rebase，也不以自动 `git revert` 代替科研决策。

受控迭代适合真正有可比较 metric 的问题；开放式探索、方法选择、机制判断或“哪种结果更显著”不能为了自动循环而强行压成一个分数。

## 8. Attempt 状态

Attempt workflow state：

```text
planned | completed | selected | abandoned | invalid
```

- `planned`：已定义但尚未形成有效执行结果；
- `completed`：形成了可审阅结果，但尚未决定是否采用；
- `selected`：被当前 Analysis 选为正式方案；每个 Analysis 同时最多一个；
- `abandoned`：执行有效，但不再继续/不采用，必须保留原因；
- `invalid`：执行后确认违反模型、数据或实现前提，不能作为科研证据使用。

选用 Attempt 的依据是 scientific alignment、诊断、robustness、leakage/overfitting、可解释性与预先定义的决策规则，而不是哪一次 `P` 值最理想。
