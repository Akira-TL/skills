# research-tree

`research-tree` 管理科研项目中的 Objective、Question、Hypothesis、Design、Study、Analysis、Observation、Claim 及其科学关系，并维护当前主要研究分支。

它用于表示“研究问题如何从证据中生长”，而不是把科研过程压成固定版本序列。新结果可以生成新的 Question，失败分支可以保持 blocked，已解决分支可以保留历史而不被覆盖。

通常不需要用户单独调用；`akira-research` 会在需要建立、更新或切换研究分支时使用它。
