---
name: devspace-orchestration
summary: 在 DevSpace 中执行已经定义的 Agent 工作单元，按任务长度与写入隔离要求选择原生 Agent、tmux 或 Git worktree，并把真实输出交回上游流程验收。
description: 用于已经明确任务边界后，需要在 DevSpace 中启动 Agent、长时间 tmux 任务或隔离 Git worktree 的执行工作。只负责执行环境、模型、工作目录、输出收集与清理；不负责拆 Task、决定 blocking/frontier、claim/Ownership 或 Task/Gate acceptance。
---

# DevSpace 多 Agent 执行

本 Skill 是执行器，不是并行任务协调协议。它接收上游已经决定的工作单元，把任务放到合适的 Agent、tmux 或 Git worktree 中运行，再把真实输出和 Git 结果交回调用它的流程。

正式 Parallel 协作的 Execution Map、Gate、Task、claim、Ownership、frontier 与 acceptance 由 `parallel-coordinator` / `parallel-execution` 管理；Rapid / Emergency / Competition 的优先级与验证要求由各自 Router 管理。本 Skill 不修改这些状态。

## When to Use

- 上游已经明确一个或多个可执行工作单元，需要把它们放到独立 Agent 中运行。
- 长任务适合在 tmux 中持续执行并稍后收集真实输出。
- 已领取的写入型 Parallel Task 需要独立 Git worktree。
- 临时只读调查无需正式 Parallel Tracker 状态，但适合同时执行。

## When NOT to Use

- 任务还没有拆清，blocking、frontier 或 ownership 仍待决定：交回当前规划流程或 `parallel-coordinator`。
- Parallel Task 尚未完成确定性 claim，却准备创建它的实现 branch/worktree 或开始项目写入：先执行 `parallel-execution`。
- 调用方希望本 Skill 判断 Task/Gate 是否通过：验收属于 Coordinator 或当前上游流程。
- 单 Agent 可以直接完成且没有独立执行环境需求。

## 输入边界

调用本 Skill 前，上游流程应当已经给出：

- 明确的任务范围与预期输出。
- 当前工作目录或目标 repository。
- 是否允许项目写入，以及允许写入的 ownership 范围。
- 若是正式 Parallel Task：稳定 Task 引用和已成功 claim 的证据。
- 当前模式或方法论要求，例如 Rapid、Emergency、Competition 或 Matt implementation。

缺少任务范围时不要自行拆分。正式 Parallel 的写入 Task 缺少有效 claim 时保持只读并返回上游，不代替 `parallel-execution` 领取。

## 选择执行方式

按照上游给出的工作单元逐个选择执行载体，不自行扩大并发数量：

- 少量、短时、需要调用方立即收集结果的任务优先使用宿主原生 Agent，并显式选择前台或同步收集方式。
- 长时间、彼此独立或适合多个终端持续执行的任务使用 tmux 子 Agent。
- 写入任务需要 Git 隔离时使用独立 worktree；只读任务通常不需要为了形式上的隔离创建 worktree。

## 模型

每个子 Agent 必须显式指定模型，不依赖父会话隐式继承：

- 默认执行使用 `sonnet`。
- 复杂架构、根因裁决、关键审查使用 `opus`。
- 简单查找、机械核对使用 `haiku`。
- `fable` 仅用于明确需要超长上下文或重型规划的少数任务。

模型选择只影响执行载体，不改变任务 ownership、claim 或 acceptance。

## 写入隔离

只读 Agent 可以共享工作目录。

写入型 Agent 必须遵守上游已经确定的 ownership。多个写入 Task 不得同时修改同一文件或模块；需要隔离时使用独立 Git worktree。

正式 Parallel Task 的顺序是：**先由 Worker 完成 `parallel-execution` claim，再创建/进入该 Task 的实现 branch/worktree，再开始项目写入**。本 Skill 不把“创建 worktree”提前到 claim 之前。

不要把 worktree 嵌套在主项目 checkout 内。需要了解 DevSpace worktree 的恢复、共享对象数据库等环境事实时，读取 `~/.agents/references/devspace.md`。

## tmux 执行

一个调用批次只创建必要的 session / window / pane；不要为了展示并发制造空闲 Agent。

session 使用：

```text
claude-<task>-<timestamp>
```

每个子 Agent 必须显式指定工作目录、模型、任务边界和预期输出，不依赖当前 shell 隐式状态。

默认调用形态：

```bash
claude -p \
  --model sonnet \
  --permission-mode dontAsk \
  --output-format json \
  '<明确、独立、可验收的任务>'
```

通过 `tmux capture-pane`、进程状态或结构化输出确认任务结束。

## 输出与清理

本 Skill 的完成产物是**执行证据**，不是 acceptance：

- 子 Agent 的实际输出。
- 写入任务的实际 Git 状态、commit/diff 指针或失败状态。
- 执行过的关键命令、测试或调查证据。
- 尚未完成、失败或需要上游处理的事项。

把这些结果原样交回调用方。正式 Parallel 由 Coordinator 根据 Issue、Git 与 Gate 证据验收；临时并行由当前父流程验收。子 Agent 的“已完成”自述不构成成功证据。

任务结束后关闭对应 tmux session，并清理本次执行产生、且上游流程已确认不再需要的临时执行资源；不得遗留空闲 Agent 进程。