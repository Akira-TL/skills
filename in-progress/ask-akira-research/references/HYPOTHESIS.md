# Hypothesis Contract

Hypothesis 阶段的目标不是选择一个最喜欢的解释，而是把 Active Uncertainty 中仍然可行的 competing explanations 转成**会对可观测结果给出不同预测**的模型集合。只有这种差异才允许后续 Design 声称能够区分它们。

## 1. 进入条件

仅当以下条件同时成立时进入 `HYPOTHESIS`：

- `RESEARCH.md` 已有一个符合 [`ACTIVE-UNCERTAINTY.md`](ACTIVE-UNCERTAINTY.md) 的 primary uncertainty；
- 至少两个 plausible explanations 尚未被现有证据排除；
- 下一步需要明确这些 explanations 的不同预测，才能选择最有信息增益的 evidence。

若现有数据已经可以直接区分 explanations，直接进入 `ANALYSIS`；若问题只是缺少文献事实，回到 literature/evidence retrieval，而不是机械创建 hypothesis 文档。

## 2. Hypothesis set，而不是单一故事

Hypothesis 以集合为单位设计。每个集合对应一个 Active Uncertainty，并至少包含两个真正竞争的解释。

在适用时主动考虑：

- target factor 具有直接作用；
- 共同原因同时造成 target 与 outcome；
- outcome / host state 反向造成 target 变化；
- measurement、selection、batch 或 analysis artifact 造成表观关系；
- effect 只在特定 population / context / dose / time window 成立。

这些不是固定模板；只有与当前 evidence 相容且能产生不同预测的解释才进入集合。

## 3. 每个 Hypothesis 的最小字段

当详细预测超过 `RESEARCH.md` 可承载的短状态时，在项目中按需创建 `hypotheses/<slug>.md`。该文件是当前 hypothesis set 的 canonical working artifact；`RESEARCH.md` 只保留 Active Uncertainty 与 pointer，不复制全部预测矩阵。

推荐结构：

```text
# Hypothesis Set: <name>

## Target Uncertainty
<与 RESEARCH.md 相同的 primary question>

## H1 — <short name>
Statement: <在明确 scope 下的解释>
Key assumptions:
- ...
Predictions:
- If <measurement/condition>, expect <observable result>.
Falsifiers:
- <result that would materially weaken H1>

## H2 — <short name>
...

## Discriminator Matrix
| Evidence / result | H1 predicts | H2 predicts | Interpretation if observed |
| ... | ... | ... | ... |

## Current Evidence
- <pointer to research-db evidence / Paper IDs / analysis artifact>

## Decision Boundary
<什么结果足以改变路线；什么结果仍不能区分>
```

`Statement` 必须带 scope。比如“Blautia A causes adaptation”过宽；“在目标人群和暴露定义下，Blautia A 的变化对某个预定义 host adaptation phenotype 具有独立可干预贡献”才是可设计检验的 target。

当 `hypotheses/<slug>.md` 已成为后续 Design / Analysis 将依赖的 canonical hypothesis set 时，使用 `research-db record-hypothesis-set` 登记其身份、target uncertainty 与 artifact path；进入结果判别前的冻结状态时同时记录真实 Git `freeze_commit`。这里 `hypothesis_sets.status=draft/frozen/closed/superseded` 描述的是 **Hypothesis Set artifact 的版本/生命周期状态**，不是结果出现后的科学可信度。数据库只保存这一最小 provenance，不复制 H1/H2、Prediction 或 Discriminator Matrix 的科研语义正文。

## 4. Prediction discipline

Prediction 必须在看到将用于判别的新结果前写清楚，避免结果出来后把 explanation 改写成永远正确的故事。

一个有效 discriminator 至少满足：

- H1 与 H2 对同一个 observation 给出不同方向、大小、时间顺序、条件依赖或 intervention response；
- measurement 能够实际区分这些差异，而不是两个模型都接受的模糊结果；
- 预测写在 observable 层，不用“机制更强”“更适应”一类未操作化词替代 measurement；
- 非显著结果只有在 design、power / precision 与区间足以区分预测时才有判别力。

若两个 hypotheses 在所有可行 measurement 上都做出相同预测，它们在当前研究问题下应合并，而不是继续制造伪竞争。

## 5. Evidence 与状态

已有论文 Claim 不自动成为本项目 Hypothesis；项目 Hypothesis 是为当前 Active Uncertainty 构造的解释模型。其当前 plausibility 必须通过 `research.sqlite` 中的 Observation / Claim / Issue 或项目自己的分析 artifact 回溯。

单个 hypothesis 的科学状态只描述当前 evidence boundary：

- `live`：尚未被当前证据区分；
- `favored`：相对竞争解释更符合当前判别证据，但仍保留适用范围；
- `weakened`：关键预测受到可信 evidence 挑战；
- `ruled_out_within_scope`：在明确 scope 和 decision boundary 下被足够判别性的 evidence 排除。

不使用 `proven` / `confirmed` 作为常规终态。一次 completed Analysis 对整个 Hypothesis Set 的结果后判别，使用 `research-db record-hypothesis-evaluation` 保存为不可覆盖的 Evaluation 事件，并区分 `unresolved`、`partially_resolved`、`resolved` 与 `not_interpretable`。Evaluation 必须指回当前 Analysis 已登记的解释/结果 artifact；它记录“这次证据做了什么”，而不是覆盖 Hypothesis Set 的结果前 freeze 历史。单个 H1/H2/H3 的 `live/favored/weakened/...` 仍写在 canonical hypothesis artifact 中，不拆成数据库行。

## 6. 完成条件

Hypothesis 阶段完成时必须有：

1. 一个与 Active Uncertainty 对齐的 hypothesis set；
2. 至少一个能区分主要 competing hypotheses 的 observable prediction；
3. 明确的 discriminator / decision boundary；
4. 下一步 evidence 是否已存在于当前数据中、需要额外分析，还是必须进入新 Design 的判断；
5. 若已形成独立 canonical `hypotheses/<slug>.md`，其 provenance 已登记；若该集合将作为后续确认性设计/分析的判别依据，已在结果出现前形成 Git freeze。

只有第 4 项指向新的 sampling、measurement、control 或 intervention 时才按 [`DESIGN.md`](DESIGN.md) 进入 `DESIGN`。
