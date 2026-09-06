---
name: parallel-execution
description: 当执行工作项带有 Execution Map、Parent Gate 或 Parallel Task 元数据，或并行协调流程需要统一 Task 生命周期、claim 与 Worker 汇报语义时使用；只补并行协作协议，不替代 Matt implement、TDD 或 code-review。
---

# Parallel Execution

本 Skill 是工程执行流程外侧的并行协作增量。它只定义并行任务（Parallel Task）的领取、状态、上下文恢复与执行 Agent（Worker）汇报；有 Matt Ticket 的写入任务继续由 Matt `implement`、`tdd`、测试与 `code-review` 负责，Akira 特殊模式产生的任务则继续遵守当前模式已经确定的执行策略。

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
2. 重新读取 Task，确认 blocker 已满足、Coordinator 没有取消或改写当前执行范围，并确认当前状态允许本 Worker 领取：普通 Task 必须为 `ready-for-agent`；`changes-requested` 只能由其保留的 Ownership Worker 重新领取；`blocked` 本身不可领取，必须先按第 4 节由 Coordinator 恢复为 `ready-for-agent`。若 `ready-for-agent` Task 已保留某个 Worker 的 Ownership，也只能由该 Worker 领取，除非 Coordinator 已明确解除或重分配 Ownership。
3. 用一次 Tracker 更新把 Ownership 与 Status 投影为当前 Worker / `in-progress`，随后重新读取并核对。
4. Tracker 更新、复核或前置条件任一步失败时，把 Tracker 恢复到领取前状态（若发生过写入），释放刚取得的互斥，再用 `status` 验证互斥已经消失；任何回滚无法确认时继续保持只读并报告 Coordinator。
5. 互斥失败时不写 Tracker。

完成条件：Tracker 与确定性 claim 对同一 Task、同一 Worker 一致，Task 状态为 `in-progress`。

### 确定性 helper

使用当前 `parallel-execution` Skill 的 sibling 脚本 `scripts/parallel_claim.py`。`<skill-root>` 表示当前已加载 Skill 的实际根目录，不要把脚本复制到项目仓库：

```bash
uv run <skill-root>/scripts/parallel_claim.py status \
  --task '<stable-task-reference>' --repo '<worktree>'

uv run <skill-root>/scripts/parallel_claim.py claim \
  --task '<stable-task-reference>' --owner '<worker-identity>' --repo '<worktree>'

uv run <skill-root>/scripts/parallel_claim.py release \
  --task '<stable-task-reference>' --owner '<worker-identity>' --repo '<worktree>'
```

`stable-task-reference` 使用 Tracker 中能唯一定位该 Parallel Task、且不随 worktree 根目录变化的稳定引用。外部 Issue Tracker 使用其稳定 issue reference；repository 内的本地 Tracker 使用 repository-relative issue 路径，例如 `tracker/tasks/implement-alpha.md`，不使用 worktree-local 绝对路径或仅供展示的标题。helper 对指向当前 worktree 内现有 Task 文件的绝对路径会归一成同一 repository-relative identity，以兼容已有调用。`worker-identity` 必须在当前 Worker 会话内稳定且能与 Tracker Ownership 对应；多个 Agent 共用同一 GitHub/GitLab 用户时不能只填共享账号名。

helper 通过 `git rev-parse --git-common-dir` 把同一 repository 的所有 worktree 映射到同一个 claim store，并对 canonical Task identity 使用原子文件创建决定唯一 winner。为兼容旧版本，它查询和释放时会识别遗留的 worktree-local absolute-path claim record；若同一 canonical Task 已存在多个不同 owner，helper fail-closed，不猜测 winner。claim 文件只是同机互斥的实现细节，**不是第二套协作状态**；Issue Tracker 仍是唯一 canonical collaboration state。`status` 在 claim store 尚不存在时不会创建目录，因此 claim 前的查询保持只读。

CLI 退出码：`0` 表示操作成功或查询成功；`1` 表示可预期的 ownership 冲突；`2` 表示 Git 环境、元数据或文件系统状态无法安全确认。`claim` 对同一 Task + owner 是幂等的；不同 owner 只有一个可以成功。

## 3. 恢复实现上下文

Claim 成功后按引用链读取，而不是依赖 Worker 自述：

1. Parent Gate：确认当前 Gate、Goal、Entry Conditions、Exit Gate 与 Integration Ref。
2. Source Matt Ticket（若存在）：确认这个 Parallel Task 对应的纵向交付范围与 blocking 关系。
3. Source Spec 与相关 ADR（若存在）：恢复跨 Ticket 的 Implementation Decisions、接口、Schema/API contract 与 Testing Decisions。
4. Akira Mode Work State（若该 Task 来自 Rapid / Emergency / Competition）：恢复当前模式、已经确认的切片或 incident scope、关键路径和验证要求；不要为了进入 Parallel 补造 Matt Spec/Ticket。
5. Parallel Task：只读取当前任务的执行范围、Acceptance Criteria、Blocked by、Ownership，以及存在时的 Provides / Consumes / Shared dependencies / Integration Notes。

Parallel Task 不替代上游工作来源。有 Matt Ticket 时，Matt Ticket 不替代 Source Spec/ADR；来自 Akira 特殊模式时，Parallel 也不重新定义该模式的 Work State 或 Execution Policy。

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

- `blocked`：Worker 已领取但出现真实外部 blocker；记录 blocker 与 Coordinator 所需动作。Task 离开 `in-progress` 后按统一规则释放 claim，并保留 Ownership。
- `changes-requested`：Coordinator 审查未通过；原 Worker默认保持 Ownership。该 Worker 恢复工作时可以在 `changes-requested` 状态重新取得 deterministic claim，成功并复核后回到 `in-progress`。
- `cancelled`：Coordinator 取消该 Task；Worker 停止继续实现。

`blocked` 的恢复由 Coordinator 驱动：只有在 Coordinator 能从 Tracker / 外部证据确认 blocker 已解除后，才把 Task 从 `blocked` 更新为 `ready-for-agent`，同时删除或明确标记已解除的 blocker。默认保留原 Ownership，因此恢复后的 Task 只允许该 Worker 重新领取；若需要换人，Coordinator 必须在恢复时或恢复前明确解除 / 重分配 Ownership。Coordinator 只恢复协作状态，不替 Worker 取得 deterministic claim；Worker 随后仍走第 2 节完整 claim transaction 再进入 `in-progress`。

权限边界：

- Worker 可以把自己已领取的 Task 更新为 `in-progress`、`blocked` 或 `ready-for-review`。
- Coordinator 才能把 Task 更新为 `accepted`、`changes-requested` 或 `cancelled`，并负责已解除 blocker 的 `blocked → ready-for-agent` 恢复以及显式 Ownership 重分配。
- Worker 不直接 close Parallel Task，也不自行宣布 Gate 通过。

当 Task 离开 `in-progress` 时，先把新的 Task 状态可靠写入并复核 Tracker，再用 helper `release` 释放执行期互斥，最后用 `status` 验证已释放。释放失败或结果不确定时不继续新的实现写入，立即把残留 claim 作为 Coordination impact 报告 Coordinator。Ownership 仍保留在 Tracker，直到 Coordinator 接受、取消或明确重新分配。

## 5. Worker 执行

协作预检完成后先按 Task 自身范围判断是否允许生产写入：

- **有 Source Matt Ticket 的写入型 Task**：继续 Matt 的实现方法。使用 Matt `implement` 执行当前 Task，按 Matt `tdd` 与项目测试约束验证行为，使用 Matt `code-review` 完成 Worker 层审查，并按当前项目 Git 原子提交规则形成归属明确的 commit。
- **来自 Akira 特殊模式的写入型 Task**：继续当前 Rapid / Emergency / Competition 已选择的 execution 分支；Parallel 只增加领取、状态和汇报，不把模式重新包装成 Matt `implement` ceremony。需要 Matt 的专业能力时仍按当前模式 Router 原有边界调用。
- **明确只读的调查 Task**：不进入 `implement`，不创建实现 branch/worktree，不修改 production/test 或写入调查交付物，也不制造调查 deliverable commit。第 2、4 节要求的 Tracker lifecycle projection 仍然执行；若本地 Tracker 由 Git 跟踪，可以形成只包含当前 Task Ownership / Status / blocker / Acceptance Criteria 等生命周期状态的 Tracker lifecycle commit，这类 commit 是协作状态证据，不把只读 Task 变成写入型 Task。按 Task 要求返回可复核事实、命令/位置、证据与它支持或排除的判断；需要专业方法时仍复用相应 Matt 能力，例如 `diagnosing-bugs` 或 `research`。

Worker 只执行当前 Task。若发现需要拆分/合并 Task、改变 blocker、移动 Gate、重画 ownership 或新增跨 Task 约定，不直接修改全局拓扑；先向 Coordinator 报告，由 Coordinator 决定并更新 Tracker。

## 6. 进入 ready-for-review

只有以下证据都存在时，Worker 才能把 Task 更新为 `ready-for-review`：

- Task Acceptance Criteria 已逐项核对。
- 目标测试、检查或调查证据已记录结果。
- 写入型 Task 已形成归属明确的 commit，完成 Matt `code-review`，并处理当前范围内必须修复的问题。
- 明确只读的调查 Task 能给出可复核事实与证据，并确认除协议必需的 Tracker lifecycle state 外没有留下 production/test、调查交付物或其他越界写入。Git-backed Tracker 的 lifecycle commit 可以存在，但必须只承载当前 Task 的协作状态；该 Task 的 delivery commit 仍为 `none`。
- Task、Parent Gate 与其真实上游来源（Source Matt Ticket 或 Akira Mode Work State）的对应关系可从 Tracker 复核；写入型 Task 还必须能从 Git 复核对应 commit。

更新并复核 `ready-for-review` 后按本 Skill 的统一释放规则释放执行期互斥，保留 Ownership，等待 Coordinator 审查。

## 7. Worker 阶段汇报

每次阶段性完成，以及最终进入 `ready-for-review`、`blocked` 或恢复 `changes-requested` 时，都在面向用户的回复中给出一个简短可复制文本块：

```text
Map: <Execution Map>
Gate: <Parent Gate>
Task: <Parallel Task>
Status: <current status>
Delivery commit(s): <写入型 Task 的交付 commit ids；只读 Task 为 none>
Lifecycle commit(s): <Tracker lifecycle commit ids or none>
Completed / Delivered: <本阶段完成内容>
Validation: <测试、检查、review 结果>
Coordination impact: <none，或需要 Coordinator 处理的 blocker / topology / integration 影响>
Coordinator action: <下一步需要 Coordinator 做什么>
```

文本块保持短，只做跨会话索引。Coordinator 验收时仍读取真实 Issue、Git commit、diff、测试与 Parent Gate。
