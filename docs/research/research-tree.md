# research-tree

`research-tree` 管理科研项目中的 Objective、Question、Hypothesis、Design、Study、Analysis、Observation、Claim 及其科学关系，并维护当前主要研究分支。

它用于表示“研究问题如何从证据中生长”，而不是把科研过程压成固定版本序列。新结果可以生成新的 Question，失败分支可以保持 blocked，已解决/关闭分支保留历史而不被覆盖；Node 进入 `closed` 时必须记录关闭原因。

当用户只有宽泛兴趣、现象描述或一句模糊 Idea 时，`research-tree` 不会直接替用户生成一个漂亮题目。它先判断研究对象、科学目标、关键未知、可区分的 competing explanations、现实资源边界和真正能改变判断的下一条 evidence 哪些仍不清楚，只追问会改变科研路线的少量问题；必要时先做低成本 Literature Discovery 建立术语、领域已知事实和真实争议。只有足以形成可行动 Research Question / Active Uncertainty 后才进入正式树结构，避免把“想研究某领域”伪装成已经定义好的科学问题。

科研项目同时使用 Git 保存执行拓扑。`main` 固定表示当前已经接受的 canonical research state；真实科研路线分叉使用 `research/<kind>/<slug>`，其中 `kind` 只取 `question|design|study|analysis`。同一路线里的参数/配置执行用 Git commit + Analysis Attempt 表示，不为每次运行开 branch。接受路线使用保留拓扑的普通 merge（例如 `--no-ff`）进入 `main`；关闭但不 merge 的路线先用 `research-closed/<kind>/<slug>` annotated tag 固定 tip，再归档并删除普通 branch。

Research Tree 的 workflow state 与 Git branch disposition 分开保存，分支名不编码 `active/blocked/closed`。已进入科研 provenance 的 Git commit/branch 历史不再通过 rebase/reset/amend 等方式重写。

通常不需要用户单独调用；`akira-research` 会在需要建立、更新或切换研究分支时使用它。
