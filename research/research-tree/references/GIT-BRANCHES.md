# 科研 Git 分支契约

Git 负责保存科研代码、配置、人类可读科研文本和小型 canonical result 的版本演化；Research Tree / `research.sqlite` 负责保存科学语义、workflow state、分叉原因和关闭原因。两者通过 Research Node、Git branch/ref 与 commit 互相定位，但任何一方都不替代另一方。

## 1. `main` 是 canonical research state

`main` 固定表示当前已经接受、允许后续研究继续依赖的科研状态。尚未接受的研究路线不得为了方便直接在 `main` 上反复试错。

科研分支统一命名：

```text
research/<kind>/<slug>
```

其中：

```text
kind = question | design | study | analysis
slug = lowercase-kebab-case
```

例如：

```text
research/question/altitude-response-shape
research/design/longitudinal-validation
research/study/yak-altitude-followup
research/analysis/nonlinear-altitude-effect
```

分支名不编码 `active/blocked/closed` 等 workflow state，不编码 Attempt 编号，也不复制完整祖先路径。状态由 Research Tree 保存；真实父子关系由 Research Tree 和 Git commit graph 共同恢复。

## 2. commit 与 branch 的粒度不同

一次参数、配置、seed、兼容修复或同一分析方案中的可重放执行状态用 Git commit + Analysis Attempt 表达，不为每次执行开新 branch。

只有科学路线真正分叉时才建立新的 Research Node 和 Git branch，例如：

- Research Question 改变；
- estimand、population、unit of inference 或 confirmatory target 实质改变；
- Study / Design 成为可独立推进的替代路线；
- Analysis 回答了不同科学问题，而不是同一分析的小参数变化。

Research branch 创建后应在仍为 `active` 时立即使用 `research-db record-research-branch` 登记，以固定真实 `base_commit`。不能等 merge/archive 后再事后推断分叉点。第一次登记后的 branch tip 允许再多一个只修改 `.research/research.sqlite` 的 provenance commit；只要代码、配置、科研 Markdown 或结果发生变化，就必须重新同步 branch provenance。

由于 `research.sqlite` 是 Git 跟踪的 canonical structured state，打开科研分支后对应的 canonical `main` 基线必须保持冻结，直到决定该路线是否接受。若 `main` 已经接受其他路线并推进，旧 sibling branch 不得直接 merge 到新的 `main`；应归档旧路线，或从当前 `main` 建立新的 Research Node / branch，继承仍然成立的思路和代码。这个约束避免把两个已经独立演化的 SQLite 状态当成普通文本自动合并。

## 3. 不重写已经进入科研 provenance 的历史

Research branch 或 Analysis Attempt 一旦有 commit 被登记到 `research.sqlite`，该历史不再通过 `rebase`、`reset`、`commit --amend`、force push 等方式重写。需要修改时追加新 commit / 新 Attempt；科学身份已经改变时建立新 Research Node / branch。

`record-research-branch` 会保留首次登记的 `base_commit`，并要求已登记的旧 tip 仍是新 tip 的祖先，从而拒绝明显的历史改写。

## 4. 接受路线：保留拓扑 merge 到 main

某条路线被接受为 canonical research state 时：

1. 先完成该 branch 上应保留的科研代码、配置、Markdown、SQLite provenance 与小型 canonical result，并确保 `main` 自分叉后没有推进；
2. 使用保留拓扑的普通 merge，例如 `git merge --no-ff research/analysis/<slug>`；
3. merge commit 的第一父节点必须等于该 branch 首次登记的 `base_commit`，否则说明 canonical baseline 已改变，该旧路线不能直接接受；
4. merge 后立即用 `research-db record-research-branch` 把 disposition 记录为 `merged`，并留下接受/关闭原因；
5. 提交本次 merge provenance；branch commit 已从 `main` 可达后，普通 branch 可以删除。

不要用 squash merge、fast-forward 或历史重写抹平承担科研 provenance 的分支拓扑。

## 5. 放弃路线：annotated archival tag

关闭且不 merge 的路线不能只删除 branch，否则 commit 最终可能成为不可达历史。归档顺序固定为：

1. 在 branch 上先把 Research Node 置为 `closed` 并填写 `closure_reason`；
2. 使用 `research-db record-research-branch` 把 disposition 记录为 `archived`；此时 archival tag 必须还不存在；
3. 提交这次只包含 closure / SQLite provenance 的收尾 commit；
4. 在该 closure commit 上建立 annotated archival tag：

```text
research-closed/<kind>/<slug>
```

例如：

```text
research-closed/analysis/linear-altitude-effect
```

archival tag 必须是 annotated tag，不能用 lightweight tag，也不能以后移动既有 tag。tag 所指 closure commit 可以晚于最后一个科研内容 tip，但两者之间只允许 `.research/research.sqlite` provenance 变化。完成后普通 branch 可以删除；该 branch 自己的 SQLite snapshot 与 tag 共同保留“从哪里分叉、做到哪里、为什么不再继续”，而未接受的科学内容不会进入 `main`。

## 6. workflow state 与 branch disposition 分开

Research Node 的 workflow state：

```text
open | active | blocked | resolved | closed
```

Git branch disposition：

```text
active | merged | archived
```

两者回答不同问题。`blocked` branch 仍可能保持 active Git branch；`resolved` Scientific Node 也可能等待 merge。Node 进入 `closed` 时必须保存 `closure_reason`，不能只留下时间戳。
