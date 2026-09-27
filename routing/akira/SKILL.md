---
name: akira
description: 判断当前项目缺少哪类 Akira / Matt / Research / Knowledge 能力并选择最小入口 Package；当开始新项目、当前任务需要尚未可用的 Skill、用户询问应安装什么能力，或需要安装、更新、移除与诊断 Skill 时使用。
compatibility: Skill 生命周期动作要求 Skiloom CLI >= 0.8.15，并要求目标已建立 Skiloom accepted state；Akira 不提供私有 installer fallback。
---

# Akira Skill Router

`akira` 只负责能力选择与跨产品路由。Skill Package 的解析、依赖闭包、source resolution、安装、更新、移除、Target ownership、同步、修复与恢复统一交给 Skiloom；不得再维护第二套安装器、Registry、Store、manifest 或 Target 写入逻辑。

执行 Skill 生命周期动作前必须具备 Skiloom CLI，并优先实际加载 Skiloom Router / 对应 specialist。由于当前 Skiloom first-party 仓尚无可供默认 Release resolver 使用的正式 Release，`akira` 不把 Skiloom Router 写成跨仓 `*` Package dependency；Lattice bootstrap 先通过公开 `skiloom install ... --git main` 显式建立 Skiloom Router / specialist direct requirement。若 CLI 或 Skiloom Target 前置条件缺失，停止生命周期动作并报告 blocker；不得退回已废弃的 Akira 安装脚本。

## 1. 先判断缺少什么能力

先检查当前会话是否已经真实具备所需 Skill；已经可用时直接交给真实 Owner，不因为 Catalog 中存在更新候选就主动扩大安装范围。

需要新增能力、确认当前 Target 状态或执行生命周期动作时，读取 [`references/CATALOG.md`](references/CATALOG.md)。Catalog 只负责把“需求”映射到入口 Package coordinate、Primary Router / Owner 与当前 source mode；它不维护依赖闭包。

当前 Target 的安装事实由 Skiloom Registry / Target state 决定。需要确认时使用：

```text
skiloom status --scope user --json
```

不要通过扫描目录、读取旧 `~/.agents/akira-skills.json` 或检查旧 `~/.agents/sources/` 来推断安装状态。

完成标准：已经确定当前任务应直接使用现有能力，还是需要一个明确的入口 Package coordinate。

## 2. 只选择入口 Package

单一通用能力选择对应单一 Package。持续专业工作选择该产品的 Primary Router Package：

- 软件工程 → `ask-akira`
- Research series → `akira-research`
- Review series → `akira-review`
- Knowledge → `akira-knowledge`

不要在 Router 中手工枚举这些入口的完整子 Skill 集合。完整 dependency closure 只由各 Package 的 `skiloom-package.toml` 与 Skiloom resolver 决定。

跨域需求出现时再增加第二个入口 Package；不得因为“以后可能需要”把 Akira 变成全家桶依赖。

## 3. 安装前先生成 Skiloom 计划

对尚未接受的能力先走公开 Candidate 操作。当前 first-party Package 尚以 Git `main` 作为 source mode 时，使用：

```text
skiloom install <coordinate> --git main --scope user --plan --json
```

读取 `SKILOOM-CLI-V1` 结构化结果，至少核对 direct requirement、exact source revision、Candidate Package / dependency graph、source delta、projection / activation name、warning 与 compatibility risk。

`--json` 只选择结构化输出，不代表批准。

若用户本轮已经明确要求安装该具体能力，可把该请求作为本次 Candidate 操作的明确授权；若安装是 Router 主动建议，则先向用户展示计划中与决策相关的来源、入口 Package、主要新增依赖与 Target 影响，再取得明确同意。

## 4. 只通过 Skiloom 提交状态变化

获得明确授权后：

```text
skiloom install <coordinate> --git main --scope user --yes --json
```

更新、移除、同步、修复、恢复、重命名、detach / rebind / forget 等动作统一加载并遵守 `skiloom-manage`，使用对应公开 CLI。

不得直接写 Skiloom Registry、Package Store、`.skiloom-state`、Target 中的受管投影、旧 Akira manifest 或旧 Akira source / symlink 注册结构。

不得为了绕过 Skiloom 的 source authorization、operation lock、ownership preflight、Store verification、Target reconciliation 或 recovery 规则而操作文件系统。

## 5. 外部能力仍先发现与审计

first-party 能力不足时读取 [`references/EXTERNAL-SOURCES.md`](references/EXTERNAL-SOURCES.md)。

候选发现优先使用 `skiloom-discover` / `skiloom search`；用户选定候选后，再把它收敛为明确 Package coordinate 与 source mode，交给 `skiloom-manage` 走同一 Candidate acceptance 流程。

外部来源出现在清单中不等于 Skiloom 已接受其 Package。若当前 upstream 不能通过 Skiloom Package admission，保持 blocker；不得调用旧安装器绕过标准。

## 6. 安装后交给真实 Owner

状态变化成功后，只确认所需入口 Package 已成为 Target 的 accepted projection，然后立即交给 Catalog 中记录的 Primary Router / Owner。

`akira` 不复制 Research、Review、Matt 或 Knowledge 的内部方法，也不根据 Catalog 推测其依赖关系。新的能力缺口重新从第 1 步判断。
