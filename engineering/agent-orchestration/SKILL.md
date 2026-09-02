---
name: agent-orchestration
summary: 在当前 Agent harness 已提供并行执行能力时，把已经定义好的工作单元映射到其原生 Agent、进程或 Git worktree，并把真实执行结果交回上游流程。
description: 用于任务边界已经明确，且当前 harness 确实提供子 Agent、进程、终端会话或 Git worktree 等执行原语的场景。只负责把既有工作单元落到当前可用执行能力并收集结果；不负责拆 Task、决定 blocking/frontier、claim/Ownership 或 Task/Gate acceptance，也不假设具体产品、CLI、模型名称或并行实现存在。
---

# Agent 编排

本 Skill 是可选的执行适配层，不是 Parallel 协议依赖。它只在当前 harness 已经提供合适执行原语时，把上游已经定义好的工作单元映射到这些原语；若当前环境没有子 Agent、后台进程、终端会话或 worktree 管理能力，就继续使用当前可用方式执行，不假设不存在的执行原语。

Codex、Claude Code 或其他 Agent harness 都可以承担实际执行；本 Skill 不把任何一种实现写成协议前提。

正式 Parallel 协作的 Execution Map、Gate、Task、claim、Ownership、frontier 与 acceptance 由 `parallel-coordinator` / `parallel-execution` 管理。Rapid / Emergency / Competition 的优先级与验证要求由各自 Router 管理。本 Skill 不修改这些状态。

## When to Use

- 上游已经给出一个或多个明确工作单元，当前 harness 又确实支持独立 Agent 或进程执行。
- 已领取的写入型 Parallel Task 需要当前 harness 提供的 Git 隔离能力。
- 少量临时只读调查可以安全并行，且当前 harness 有合适原语。
- 调用方需要统一收集多个执行单元的真实输出、退出状态或 Git 结果。

## When NOT to Use

- 任务还没有拆清，blocking、frontier 或 Ownership 仍待决定：交回当前规划流程或 `parallel-coordinator`。
- Parallel Task 尚未完成确定性 claim，却准备创建任务专属 branch/worktree 或开始项目写入：先执行 `parallel-execution`。
- 当前 harness 没有对应并行原语：不要因为本 Skill 存在就模拟一套并行运行环境。
- 调用方希望本 Skill判断 Task/Gate 是否通过：验收属于 Coordinator 或当前上游流程。
- 单 Agent 直接执行已经足够。

## 输入边界

调用前，上游流程应当已经给出：

- 明确任务范围与预期输出。
- 当前工作目录或目标 repository。
- 是否允许项目写入，以及允许写入的 Ownership 范围。
- 若是正式 Parallel Task：稳定 Task 引用和已成功 claim 的证据。
- 当前模式或方法论约束，例如 Rapid、Emergency、Competition 或 Matt implementation。

缺少任务范围时不要自行拆分。正式 Parallel 的写入 Task 缺少有效 claim 时保持只读并返回上游，不代替 `parallel-execution` 领取。

## 发现当前 harness 能力

先使用当前会话已经暴露的工具契约判断实际可用能力，不根据产品名称猜测：

- 是否支持原生子 Agent，以及同步/异步结果收集方式。
- 是否支持本地或远程进程、终端会话。
- 是否支持创建或进入 Git worktree。
- 是否需要显式选择模型、权限模式或工作目录。
- 是否提供结构化输出、退出状态或可复核日志。

只使用已经确认存在的能力。不同 harness 的命令、参数、模型名称和生命周期可以不同，不在本 Skill 中建立跨产品映射。

## 执行

按照上游给出的工作单元选择当前 harness 中最简单、可复核的执行方式，不自行扩大并发数量：

- 短时任务优先使用当前 harness 的原生子 Agent 或等价同步执行原语。
- 长时间任务只有在当前 harness 提供可靠的后台/终端生命周期与结果收集能力时才独立运行。
- 写入任务需要 Git 隔离时，使用当前环境实际支持的标准 Git worktree 或等价隔离方式。
- 只读任务通常不需要为了形式上的隔离创建额外工作树。

若当前 harness 要求显式模型或执行配置，则遵守该 harness 与项目已经定义的模型策略；不要假设 Codex、Claude Code 或其他 harness 共享同一模型名称。

## 写入边界

只读 Agent 可以共享工作目录，只要当前工具契约不会产生隐式项目写入。

写入型 Agent 必须遵守上游已经确定的 Ownership。多个写入 Task 不得同时修改相同所有权范围。

正式 Parallel Task 的顺序固定为：**Worker 先完成 `parallel-execution` claim，再创建或进入该 Task 的任务专属写入环境，再开始项目写入**。执行适配层不得把任务专属 branch/worktree 创建提前到 claim 之前。

## 输出

完成产物是执行证据，不是 acceptance：

- 实际 Agent / 进程输出与退出状态。
- 写入任务的实际 Git 状态、commit/diff 指针或失败状态。
- 执行过的关键命令、测试或调查证据。
- 尚未完成、失败或需要上游处理的事项。

把这些事实交回调用方。正式 Parallel 由 Coordinator 根据 Issue、Git 与 Gate 证据验收；临时并行由当前父流程验收。子 Agent 的“已完成”自述不构成成功证据。

任务结束后只清理本次调用创建、且已确认不再需要的执行资源。具体清理方式由当前 harness 的生命周期语义决定。
