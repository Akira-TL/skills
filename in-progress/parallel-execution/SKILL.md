---
name: parallel-execution
description: 当实现工作项带有 Execution Map、Parent Gate 或 Parallel Task 元数据，或并行协调流程需要统一 Task 生命周期、claim 与 Worker 汇报语义时使用；只补并行协作协议，不替代 Matt implement、TDD 或 code-review。
---

# Parallel Execution

本 Skill 是 Matt 实现流程外侧的并行协作增量。它只定义并行任务（Parallel Task）的领取、状态、上下文恢复与执行 Agent（Worker）汇报；工程实现仍由 Matt `implement`、`tdd`、测试与 `code-review` 负责。

Issue Tracker 是协作状态的唯一事实来源。Worker 的口头汇报只是跨会话索引，不替代 Issue、Git commit、diff 或测试证据。

## 1. 识别 Parallel Task

满足任一条件即按 Parallel Task 处理：

- 工作项明确标记为 Parallel Task。
- 工作项包含执行地图（Execution Map）或父门禁（Parent Gate）引用。
- 工作项是 Parallel Gate 的 child Issue。

普通 Matt Ticket 不进入本协议。

## 2. 领取（claim）是第一项写操作

Worker 可以在 claim 前只读查看 Execution Map、Parent Gate 与 frontier 索引，以判断任务是否可领取。

在深入实现、创建本 Worker 自己的实现 branch/worktree、修改生产代码或执行其他会改变项目状态的操作之前，必须先完成确定性 claim。Tracker assignee 或本地 `Status:` 只用于可见协作状态，不能在多个 Agent 共享同一账号或同一本地目录时单独承担互斥。

确定性 claim helper 属于本 Skill 的实现依赖。若 helper 不存在、不可执行或不能证明当前 Worker 已取得互斥，立即停止在只读状态；不得降级为“先写 Tracker 再观察冲突”。

Claim 的事务边界是：

1. 先取得确定性互斥。
2. 再把 Task 的 Ownership 与 Status 投影到 Issue Tracker。
3. Tracker 更新失败时释放刚取得的互斥，使两处状态回到未领取。
4. 互斥失败时不写 Tracker。

完成条件：Tracker 与确定性 claim 对同一 Task、同一 Worker 一致，Task 状态为 `in-progress`。

## 3. 恢复实现上下文

Claim 成功后按引用链读取，而不是依赖 Worker 自述：

1. Parent Gate：确认当前 Gate、Goal、Entry Conditions、Exit Gate 与 Integration Ref。
2. Source Matt Ticket：确认这个 Parallel Task 对应的纵向交付范围与 blocking 关系。
3. Source Spec 与相关 ADR：恢复跨 Ticket 的 Implementation Decisions、接口、Schema/API contract 与 Testing Decisions。
4. Parallel Task：只读取当前任务的 What to implement、Acceptance Criteria、Blocked by、Ownership，以及存在时的 Provides / Consumes / Shared dependencies / Integration Notes。

Parallel Task 不替代 Source Matt Ticket，Source Matt Ticket 也不替代 Source Spec/ADR。

如果本 Skill 是从 Matt `implement` 内部加载的，完成上述协作预检后**返回原 `implement` 流程**；不要再次调用 `implement` 形成递归。

## 4. Task 生命周期

规范生命周期：

```text
ready-for-agent
→ in-progress
→ ready-for-review
→ accepted
```

允许以下必要分支：

- `blocked`：Worker 已领取但出现真实外部 blocker；记录 blocker 与 Coordinator 所需动作。
- `changes-requested`：Coordinator 审查未通过；原 Worker 默认保持 Ownership，恢复工作时重新取得确定性 claim 后回到 `in-progress`。
- `cancelled`：Coordinator 取消该 Task；Worker 停止继续实现。

权限边界：

- Worker 可以把自己已领取的 Task 更新为 `in-progress`、`blocked` 或 `ready-for-review`。
- Coordinator 才能把 Task 更新为 `accepted`、`changes-requested` 或 `cancelled`。
- Worker 不直接 close Parallel Task，也不自行宣布 Gate 通过。

当 Task 离开 `in-progress` 时释放执行期互斥；Ownership 仍保留在 Tracker，直到 Coordinator 接受、取消或明确重新分配。

## 5. Worker 实现与提交

协作预检完成后，继续 Matt 的实现方法：

- 使用 Matt `implement` 执行当前 Task。
- 按 Matt `tdd` 与项目测试约束验证单 Task 行为。
- 使用 Matt `code-review` 完成 Worker 层审查。
- 按当前项目 Git 原子提交规则形成一个或多个归属明确的 commit。

Worker 只实现当前 Task。若发现需要拆分/合并 Task、改变 blocker、移动 Gate、重画 ownership 或新增跨 Task 约定，不直接修改全局拓扑；先向 Coordinator 报告，由 Coordinator 决定并更新 Tracker。

## 6. 进入 ready-for-review

只有以下证据都存在时，Worker 才能把 Task 更新为 `ready-for-review`：

- 当前 Task 的实现已提交。
- Task Acceptance Criteria 已逐项核对。
- 目标测试/检查已记录结果。
- Matt `code-review` 已完成，且 Worker 已处理当前范围内必须修复的问题。
- Commit、Task、Parent Gate 与 Source Matt Ticket 的对应关系可从 Tracker 与 Git 复核。

更新 `ready-for-review` 后释放执行期互斥，保留 Ownership，等待 Coordinator 审查。

## 7. Worker 阶段汇报

每次阶段性完成，以及最终进入 `ready-for-review`、`blocked` 或恢复 `changes-requested` 时，都在面向用户的回复中给出一个简短可复制文本块：

```text
Map: <Execution Map>
Gate: <Parent Gate>
Task: <Parallel Task>
Status: <current status>
Commit(s): <commit ids or none>
Completed / Delivered: <本阶段完成内容>
Validation: <测试、检查、review 结果>
Coordination impact: <none，或需要 Coordinator 处理的 blocker / topology / integration 影响>
Coordinator action: <下一步需要 Coordinator 做什么>
```

文本块保持短，只做跨会话索引。Coordinator 验收时仍读取真实 Issue、Git commit、diff、测试与 Parent Gate。
