# Akira Skill 生命周期契约

本文件定义 `akira` Router 如何把能力选择交给 Skiloom。Akira 不再拥有独立 Skill installer；所有生命周期状态变化只通过公开 `skiloom` CLI 完成。

安装“什么能力”由 [`CATALOG.md`](CATALOG.md) 决定；外部来源由 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md) 约束；Package 直接依赖由各自 `skiloom-package.toml` 声明。

## 1. 前置条件

`akira` 的生命周期动作要求宿主已经提供 Skiloom CLI `>= 0.8.15`。当前 Skiloom first-party 仓尚无可供默认 Release resolver 使用的正式 Release，因此 Skiloom Router 作为 bootstrap direct requirement 由 Lattice 用显式 Git source 建立，而不是写成 `akira` 的跨仓 `*` Package dependency。详见 `../DEPENDENCIES.md`。

先确认：

```text
skiloom --version
```

CLI 不可用时停止安装、更新、移除、同步、修复与恢复操作，并明确报告前置条件缺失。不得退回历史 `scripts/skills.py`、Git clone + symlink 或任何私有 manifest 实现。

## 2. Target 与状态事实

Lattice 的默认 Skill Target 使用 Skiloom 的用户级 scope：

```text
--scope user
```

在当前 Skiloom Host mapping 中，该默认 Target 解析到用户级 Agent Skills Target；具体路径由 Skiloom CLI 解析，不由 Akira 写死或管理。

检查状态：

```text
skiloom status --scope user --json
```

需要更完整诊断时加载 `skiloom-doctor` 并使用公开 doctor 命令。

旧 `~/.agents/akira-skills.json`、`~/.agents/sources/` 与历史 Akira-created symlink 不再具有 lifecycle authority。它们不得作为“已安装”“当前 revision”或“允许更新”的事实来源。

## 3. Candidate 计划

从 Catalog 得到入口 Package coordinate 后，先生成计划。当前 first-party 仓尚以 Git `main` 作为正式 source mode：

```text
skiloom install <coordinate> --git main --scope user --plan --json
```

读取 `SKILOOM-CLI-V1`，根据任务至少检查 direct requirements、exact sources、packages、dependency edges、source deltas、projections、renames、detached-content risks 与 warnings。

Skiloom resolver 负责递归 dependency closure。Akira 不再展开 `--skill` 列表、不扫描 repository root，也不决定依赖安装顺序。

## 4. Candidate 接受

只有用户已明确授权该状态变化后才提交：

```text
skiloom install <coordinate> --git main --scope user --yes --json
```

`--json` 不是授权；`--yes` 也不授权独立风险边界，例如 Release retarget 或 import merge。相关情况必须遵守 `skiloom-manage` 的专门规则。

## 5. 其他生命周期动作

统一加载并遵守 `skiloom-manage`：

```text
skiloom update --plan --json
skiloom update --yes --json
skiloom remove <coordinate> --plan --json
skiloom remove <coordinate> --yes --json
skiloom sync --json
skiloom repair --json
skiloom recover --plan --json
```

rename、detach、rebind、forget、observe、export / import 与其他动作同样只使用其公开 CLI 契约。

## 6. 不允许的第二写入路径

Akira 不再：

- clone / fetch Skill source 作为自己的生命周期实现；
- 维护 `~/.agents/akira-skills.json`；
- 创建或删除机器级 Skill symlink；
- 维护自己的 source checkout registry；
- 递归解析依赖；
- 通过文件系统直接修复 Target；
- 在 Skiloom 失败时 fallback 到旧安装器。

也不得直接修改 Skiloom Registry、Package Store、`.skiloom-state` 或 managed projection。

## 7. first-party source mode

当前 Akira first-party 仓尚未全部提供可供默认 resolver 使用的正式 Release，因此 Catalog 明确使用 Git `main`。例如：

```text
skiloom install akira-tl/akira-research-skills/akira-research --git main --scope user --plan --json
```

未来完成 Release 发布后，可以把 source policy 切换到 version / Release resolution；Package coordinate 与 dependency graph 不因此回退到手写 bundle。

## 8. 外部 Package

外部能力先通过 `skiloom-discover` / `skiloom search` 发现并审计。已知 GitHub source 时，也必须先形成明确 Package coordinate，并通过 Skiloom plan 验证 Package admission。

如果 upstream 因 frontmatter、package layout 或其他标准问题无法被 Skiloom 接受，保持 blocker。不得使用历史 Akira installer 绕过 admission。

## 9. Lattice bootstrap

Lattice 根安装器按以下顺序建立用户级 Target：

1. 验证 Skiloom CLI 满足最低运行要求；
2. 通过 `skiloom install akira-tl/skiloom/skiloom --git main --scope user --yes --non-interactive --json` 显式建立 first-party Skiloom Router / specialist direct requirement；
3. 再把 Akira 基础 direct requirements 安装到同一用户级 Target。

必须先建立 Skiloom Git direct requirement：当前 `Akira-TL/skiloom` 尚未发布 GitHub Release，bare `skiloom bootstrap` 在 fresh Target 会得到 `UnsatisfiableReleaseRequirements`。显式 Git source 不依赖某台机器既有状态，并保持整个 bootstrap 仍只使用 Skiloom public CLI。

当前 Akira 基础 direct requirements：

- `akira-tl/skills/akira`
- `akira-tl/skills/browser-access`

Guard 已作为 `akira` Package 的内置执行能力随包安装，不再拥有独立 Package coordinate 或 direct requirement。

`akira` 当前不声明跨仓 Skiloom Package dependency；Skiloom Router / specialist 由上述 bootstrap direct requirement 独立保持在 accepted Target state 中。后续生命周期全部由 Skiloom accepted state 继续管理。
