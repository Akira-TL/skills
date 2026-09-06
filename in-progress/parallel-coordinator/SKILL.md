---
name: parallel-coordinator
description: 以当前会话作为主 Agent，基于既有 Matt Spec/Tickets 或 Akira 模式 Work State 建立或恢复 Execution Map、Gate 与 Parallel Tasks，维护动态 frontier，并负责 Task 与 Gate 的跨任务验收。
disable-model-invocation: true
---

# Parallel Coordinator

本 Skill 把当前会话确立为并行开发的主 Agent（Coordinator）。它建立执行地图（Execution Map）、门禁（Gate）和并行任务（Parallel Task），维护动态 frontier，并负责双层验收；它不创建另一套 Spec、TDD、code-review 或 implement 方法论。

Parallel 不重写上游工程方法。标准 Matt 流程中，`to-spec` 保存跨 Ticket 的 Implementation Decisions / Testing Decisions，`to-tickets` 保存纵向交付切片与 blocking edges，Worker 写代码时继续使用 Matt `implement`、`tdd` 与 `code-review`。若 Parallel 是从 Rapid / Emergency / Competition 进入，则保留该模式已经确认的 Work State 与 Execution Policy，不为了并行补造 Matt Spec/Ticket。

进入本 Skill 后先加载 `parallel-execution`，以其中的 Task 生命周期、claim、Ownership 和 Worker Report 语义作为唯一事实来源；本 Skill 不重复定义这些规则。

## 1. 建立 Coordinator 上下文

读取并确认：

1. 配置好的 Issue Tracker 规则；协作状态只写入该 Tracker。
2. 当前上游工作来源：Matt 流程读取 Source Spec、相关 ADR、Matt Tickets 与 blocking edges；Akira 特殊模式读取当前 mode、已经确认的 Work State、切片 / incident scope / Demo Critical Path 与验证要求。
3. 已存在的 Execution Map（若用户要求恢复而不是新建）。
4. 当前 Git integration ref / fixed point；纯只读调查没有代码集成时仍记录当前基线，作为“未发生项目写入”的复核点。

`/parallel-coordinator` 的显式调用即表示当前会话承担 Coordinator 角色；若用户给出已有 Execution Map，则恢复该 Map，不另建第二份状态。

完成条件：Coordinator 能从 Tracker、当前模式上下文与 Git 指出真实上游来源、当前 integration ref，以及是否已有活跃 Gate。

## 2. 建立或恢复 Execution Map

Execution Map 是整个多 Agent 执行工作的根 Issue，只保存执行索引，不复制 Spec/ADR 正文。

最小字段：

```markdown
## Execution Policy
<Matt standard | Akira rapid | Akira emergency | Akira competition>

## Source Work
<参与本次并行执行的 Matt Ticket；或当前 Akira 模式的稳定 Work State / slice / incident scope 引用。若这些 Work State 只存在于当前对话，则在这里一次性记录执行所需的最小已确认事实，使 Execution Map 成为后续 Worker 可读取的稳定来源>

## Source Spec
<canonical spec reference；没有正式 Spec 时写 none，不为 Parallel 新建>

## Gates
<Gate 标题与引用；只做索引>

## Current Gate
<当前活跃 Gate，或 none>

## Integration Ref
<当前集成基线 / HEAD / branch reference>

## Coordination Notes
<尚未解决、确实影响并行协调的事项；没有则 none>
```

若 Map 已存在，只更新发生变化的索引与 coordination facts；不要把 Gate、Task、Spec、ADR 或模式正文复制进 Map。唯一例外是 Akira mode 的 Work State 还没有任何稳定 artifact：首次建 Map 时必须把后续 Worker 真正需要的已确认目标、切片 / incident scope / Demo Critical Path 与验证事实压缩记录到 `Source Work`，但仍不复制 Execution Policy。

`Integration Ref` 表示 Coordinator 已确认的集成 Git 状态：Gate 处于执行中时，它是该 Gate 的 integration base；Gate review 通过后，它是本轮实际审查通过的 integration HEAD。为写入 `Status: accepted`、Execution Map 或下一 Gate 状态而随后产生的 Tracker transition commit 不属于其自身所证明的 reviewed state，因此不得回写为该 Gate 的 `Integration Ref`。下一 Gate 激活时继承上一 Gate 已验收的 `Integration Ref` 作为新的 integration base。

## 3. 建 Gate

Gate 是 Execution Map 的 child Issue。Gate ID 可以使用既有项目里有意义的 `1.1.1`、`foundation`、`M1` 等标识；协议不解释其版本语义。

最小字段：

```markdown
## Gate ID
<id>

## Source Scope
<本 Gate 覆盖的 Matt Ticket / scope references>

## Entry Conditions
<进入 Gate 前必须成立的条件>

## Goal
<本 Gate 集成完成后可验证的目标>

## Exit Gate
<Coordinator 最终验收条件>

## Integration Ref
<本 Gate 的 integration base / branch / current HEAD>

## Status
<当前 Gate 状态；只有完成 Gate review 后才能写为 accepted>
```

Gate 只有 Coordinator 可以判定 `accepted`。所有 required Task 已 `accepted` 只是 Gate review 的入口条件，不等于 Gate 自动通过；其他 Gate 状态按当前执行事实记录，不另造一套固定生命周期。

## 4. 发布 Parallel Tasks

Parallel Task 是 Gate 的 child Issue，是执行期分工，不替代上游工作来源。标准 Matt 流程中它不替代 Matt Ticket；Akira 特殊模式中它不替代模式已经确认的切片、incident scope 或 Demo Critical Path。允许：

- `1 Matt Ticket = N Parallel Tasks`。
- `N Matt Tickets = 1 shared foundation Task`。
- Matt Ticket 与 Parallel Task 一一对应。

每个 Task 的最小字段：

```markdown
## Parent Gate
<Gate reference>

## Source Matt Ticket
<Matt Ticket reference；非 Matt 来源时省略>

## Source Mode Work
<Akira mode Work State / slice / incident reference；Matt 来源时省略>

## What to execute
<当前执行范围；不复制全局 Implementation Decisions 或模式策略>

## Blocked by
<Parallel Task / Gate blocker，或 none>

## Ownership
<unclaimed，或当前 Worker identity>

## Acceptance Criteria
- [ ] <criterion>

## Status
ready-for-agent
```

只有真实协作需要时才增加：

- `Task Kind: read-only`：明确禁止 production/test 与调查交付物写入的调查 Task；协议必需的 Tracker lifecycle state 不算调查交付写入，若 Tracker 由 Git 跟踪，可以形成仅承载当前 Task 生命周期状态的 Tracker lifecycle commit。普通写入 Task 不必增加该字段。
- `Provides`
- `Consumes`
- `Shared dependencies`
- `Integration Notes`

不要为了模板完整度增加空字段或 ceremony。

## 5. 维护动态 frontier

Frontier 是当前 Gate 内满足以下条件的 Task：

- `Status: ready-for-agent`。
- blocking 条件已满足。
- 没有有效 claim。

若 frontier Task 的 Ownership 为 `unclaimed`，它可以由任一合格 Worker 竞争 claim；若 Task 因 `blocked` 恢复等原因保留了某个 Worker identity，则它只对该 Worker 可领取，Coordinator 在分派 / 汇报 frontier 时必须保留这一 ownership restriction，不能把它当成公开可领取任务。需要换人时，Coordinator 先明确解除或重分配 Ownership，再允许新的 Worker claim。

Frontier 以当前 Gate、Task 的 `Status` / blocker / Ownership 与 deterministic claim 为事实依据；Execution Map 的 `Coordination Notes` 只是 Coordinator 说明，不参与 frontier 判定。Notes 若因 Worker 生命周期推进而陈旧，由 Coordinator 在下一次相关状态写入时同步，不因此扩大 Worker ownership。

并行度随 frontier 动态变化，不预先固定 Worker 数量。执行过程中可以新增、拆分、合并、取消 Task 或调整 blocker，但这些拓扑修改由 Coordinator 统一写入 Tracker。

Worker 发现需要改变拓扑时，只提交 Coordination impact；Coordinator 依据真实 Issue、Git 与 Gate 目标判断后再修改。Worker 报告的外部 blocker 已解除时，Coordinator 还负责按 `parallel-execution` 的生命周期规则核验证据并恢复 `blocked` Task；恢复状态不等于替 Worker claim。

Emergency 场景默认更保守，通常保持单 Writer + 多只读调查 Agent；Rapid / Competition 是否扩大 frontier 由对应 Akira 模式决定。本 Skill 自身不重写这些模式策略。

## 6. 验收 ready-for-review Task

Worker Report 只是索引。Task review 必须读取 Parallel Task 当前 Issue、Acceptance Criteria、Parent Gate 与真实上游来源，然后按 Task 类型取证：

- **写入型 Task**：读取 Worker commit、相对适当 fixed point 的 diff、测试/检查与当前执行策略要求的 review 结果；有 Source Matt Ticket 时同时核对 Source Spec / ADR。
- **只读调查 Task**：读取 Worker 给出的命令、位置、日志或其他可复核证据，并确认相对领取前基线没有该 Worker 留下的 production/test、调查交付物、Spec/Ticket、Gate/Execution Map/topology 或其他越界写入。Git-backed Tracker 因 claim / lifecycle 必需产生的当前 Task lifecycle commit 可以存在，必须单独识别为协作状态证据；其 delivery commit 应为 `none`。

检查至少覆盖：

- 执行范围是否落在当前 Task ownership 内。
- 写入型 Task 的 delivery commit 是否只包含归属明确的当前修改；只读 Task 是否除允许的 Tracker lifecycle state 外确实没有 production/test、调查交付物或其他越界写入，且 lifecycle commit 没有夹带交付内容。
- Task 是否满足其真实上游工作来源与 Parent Gate 的要求。
- 是否引入未协调的跨 Task 接口、共享资源或 integration 假设。

结果只有两种：

- 通过 → Coordinator 把 Task 更新为 `accepted`。
- 不通过 → Coordinator 把 Task 更新为 `changes-requested`，写明可验证的缺口；原 Worker 默认继续保留 Ownership。

Coordinator 不以 Worker 的“已完成”自述代替证据。

## 7. Gate integration review

当 Gate 所有 required Task 都已 `accepted` 后，开始 Gate review；不要自动推进下一 Gate。

若 Gate 包含代码写入，以 Gate 的 integration base → 当前 integration HEAD 为 fixed point：标准 Matt 来源优先复用 Matt `code-review` 做 Standards + Spec 审查；Akira 特殊模式按该模式原有 verification 要求验收，并在需要时复用 Matt 专业能力。若 Gate 全部是只读调查，不制造代码 review，只把跨 Task 证据组合后验证 Gate Goal / Exit Gate。

对含写入的 Gate，Coordinator 额外检查跨 Task 集成问题：

- 重复 abstraction 或重复实现。
- 跨 Task 接口漂移。
- 文件/模块拆分偏离 Source Spec / ADR。
- 临时 compatibility layer 没有明确退出路径。
- Provides / Consumes 等约定没有真正接通。
- 单 Task 都通过但组合后违反 Gate Goal / Exit Gate。

若暴露的是模块/interface 层面的真实架构问题，调用 Matt `codebase-design`；不要在本 Skill 内发明新的架构方法。

Gate review 通过后：

1. 更新 Gate `Status: accepted`，并把 `Integration Ref` 写为本轮实际审查通过的 integration HEAD。
2. 更新 Execution Map 的 Current Gate / Integration Ref；若还有下一 Gate，按上文 `Integration Ref` 语义把该 reviewed state 作为下一 Gate 的 integration base。
3. 根据既有 Gates 与新暴露的依赖刷新 frontier。
4. 只有 Entry Conditions 已满足时才激活下一 Gate。

## 8. 完成条件

一次并行执行工作只有在以下条件同时成立时才完成：

- 所有仍在本次执行范围内的 Gates 均已由 Coordinator 验收为 `accepted`；若某 Gate 被移出执行范围，Execution Map 中已记录原因。
- Execution Map 的 Integration Ref 指向最终已验收状态。
- 不存在 `ready-for-review`、`changes-requested` 或未处理的 coordination blocker。
- 最终 Git 状态与 Tracker 状态可以相互复核。

完成时向用户汇报最终 Map、Gates、关键 commits、验证结果和仍然存在的 out-of-scope 项；不要仅汇总 Worker 文本块。
