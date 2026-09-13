# Agent 编排

`agent-orchestration` 是一个可选的、与具体 Agent harness 无关的执行适配 Skill。它只负责把**已经定义好的工作单元**映射到当前环境实际提供的子 Agent、进程、终端会话或 Git worktree 等执行能力，并把真实结果交回上游流程。

它不是 Parallel 的前置依赖，也不代表系统假设存在某种固定“执行器”。Codex、Claude Code 或其他 harness 都可以承担实际执行；如果当前环境没有对应并行能力，就使用当前可用方式继续工作。

## 核心边界

Task 如何拆、谁能领取、哪些 blocker 已解除、当前 frontier 是什么、Task/Gate 是否通过，都不由本 Skill 决定。正式 Parallel 的 Execution Map、Gate、claim、Ownership 与 acceptance 仍由 `parallel-coordinator` / `parallel-execution` 管理。

正式 Parallel 写入任务遵守同一硬边界：Worker 先完成确定性 claim，再创建或进入任务专属写入环境，然后才开始项目写入。执行适配层不能提前替 Worker 创建任务专属 branch/worktree。

## 执行方式

本 Skill 先读取当前 harness 已暴露的工具契约，再决定能否使用：

- 原生子 Agent；
- 本地或远程进程；
- 终端或后台会话；
- Git worktree 或其他明确支持的隔离方式；
- 结构化输出、退出状态或日志收集。

不根据产品名称猜测能力，不硬编码特定 CLI、模型名称、权限参数或并发实现。当前 harness 要求显式模型或执行配置时，使用该 harness 与项目已有的模型策略。

## 输出与验收

执行适配层返回的是证据，而不是“已验收”结论：

- 实际输出与退出状态；
- 写入任务的 commit/diff 或失败状态；
- 关键命令、测试和调查证据；
- 尚未完成或需要上游处理的事项。

正式 Parallel 由 Coordinator 验收；Rapid、Emergency、Competition 的临时并行由当前模式流程验收。

## 安装

项目级安装只从远端 GitHub source 拉取，并在当前项目建立软链接：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill agent-orchestration \
  --project .
```
