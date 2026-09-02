# DevSpace 多 Agent 执行

`devspace-orchestration` 用于把**已经定义好的工作单元**放到 DevSpace 的原生 Agent、tmux 或 Git worktree 中执行，并把真实输出、Git 结果和失败状态交回上游流程。

它是执行层，不是任务协调层。Task 如何拆、谁能领取、哪些 blocker 已解除、当前 frontier 是什么、Task/Gate 是否通过，都不由本 Skill 决定。

## 适用场景

- 已经明确任务边界，需要启动一个或多个 Agent 执行。
- 长任务适合在 tmux 中持续运行并稍后收集结果。
- 已领取的写入型 Parallel Task 需要独立 Git worktree。
- 少量临时只读调查适合并行，但无需建立正式 Execution Map。

如果工作还没有拆清，或需要持久的 Execution Map、Gate、claim、Ownership 和动态 frontier，应先进入 `parallel-coordinator`；正式 Parallel Worker 的领取与生命周期由 `parallel-execution` 管理。

## 核心边界

正式 Parallel 中的顺序是：Worker 先完成确定性 claim，Tracker 已复核为 `in-progress`，然后执行器才可以创建该 Task 的实现 branch/worktree 或开始项目写入。`devspace-orchestration` 不代替 Worker claim，也不会因为“准备执行”就抢先创建写入环境。

临时并行没有正式 Parallel Tracker 生命周期时，可以直接使用本 Skill，但调用方仍需先给出明确任务范围、是否允许写入和预期输出。本 Skill不会自行扩大并发数或把一个任务重新拆成更多任务。

## 执行方式

短时、需要调用方立即收集结果的任务优先使用宿主原生 Agent；长时间、终端化任务使用 tmux。写入任务需要 Git 隔离时使用独立 worktree，只读任务通常不需要为了形式上的隔离创建 worktree。

每个子 Agent 显式选择模型：默认执行使用 Sonnet，复杂架构、根因裁决或关键审查使用 Opus，简单机械核对使用 Haiku；Fable 只用于明确需要超长上下文或重型规划的少数任务。模型选择不改变 ownership、claim 或 acceptance。

## 输出与验收

执行器返回的是证据，不是“已验收”结论：

- 子 Agent 的实际输出；
- 写入任务的 commit/diff 或失败状态；
- 关键命令、测试和调查证据；
- 尚未完成或需要上游处理的事项。

正式 Parallel 由 Coordinator 读取 Issue、Git 与 Gate 证据后验收；Rapid、Emergency、Competition 的临时并行由当前模式流程验收。子 Agent 自述“完成”不能替代这些证据。

任务结束后清理对应 tmux session 和确认不再需要的临时执行资源，不遗留空闲 Agent 进程。

## 与 Akira Lattice 的关系

Skill runtime source 位于：

```text
engineering/devspace-orchestration/SKILL.md
```

Akira Lattice 的全局规则只保留长期执行原则；Parallel 状态模型由 `parallel-coordinator` / `parallel-execution` 负责，DevSpace 的 workspace、linked worktree 恢复和共享 Git common directory 等工具事实继续由 Lattice reference 管理。

## 安装

从当前仓库安装：

```bash
npx skills add . --skill devspace-orchestration --agent '*' -g -y
```

也可以直接从 GitHub 安装：

```bash
npx skills add Akira-TL/skills --skill devspace-orchestration --agent '*' -g -y
```