# Akira lifecycle dependency

`akira` 的能力路由本身可以只读使用；凡涉及 Skill Package 安装、更新、移除、同步、修复、恢复或 Target 诊断，则要求：

- Skiloom CLI `>= 0.8.15`；
- 目标 Target 已由 Skiloom 建立 accepted state；
- 可用时加载 `akira-tl/skiloom/skiloom` Router / specialist instructions。

当前 Skiloom first-party 仓没有可供默认 Release resolver 使用的正式 Release，因此这里不把 `akira-tl/skiloom/skiloom = "*"` 写入 `skiloom-package.toml`。否则 fresh Target 会尝试 Release resolution 并得到 `UnsatisfiableReleaseRequirements`。

Lattice bootstrap 使用 Skiloom 自己的 first-party bootstrap 入口先建立该 direct requirement：

```text
skiloom bootstrap --scope user --yes --non-interactive --json
```

该命令由 Skiloom 自身选择 first-party Git source，并建立 Router / specialist accepted state；随后再安装 Akira 基础 Package。未来 Skiloom 提供正式 Release 后，可重新评估是否把这一 host/lifecycle prerequisite 收敛为普通 Package dependency。
