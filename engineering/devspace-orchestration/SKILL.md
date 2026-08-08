---
name: devspace-orchestration
summary: 在 DevSpace 中编排 Claude 原生 Agent、tmux 子 Agent 与 Git worktree，按任务长度、依赖关系和写入范围选择并行方式，并由父 Agent 统一验收与清理。
description: 用于 DevSpace 中需要并行子 Agent、长时间 tmux 任务、隔离写入或 Git worktree 的开发任务。负责拆分独立任务、显式选择模型、隔离修改范围、收集真实输出并清理会话。单 Agent 可以清晰完成、任务存在严格前后依赖或只是简单机械查找时不要为了并发而调用。
---

# DevSpace 多 Agent 编排

## When to Use

- 多个子任务可以独立并行，并需要父 Agent 最终汇总。
- 子任务执行时间较长，适合独立终端持续运行。
- 多个写入型 Agent 需要通过不同文件范围或 worktree 隔离。
- 需要在 DevSpace 中明确管理模型、工作目录、任务边界和验收结果。

## When NOT to Use

- 单 Agent 可以清晰、快速完成任务。
- 子任务存在严格前后依赖，上游结果未确定前下游无法执行。
- 为了展示多 Agent 而机械拆分任务。
- 多个写入任务无法安全划分文件或模块所有权，且没有独立 worktree。

## 选择并行方式

少量、短时、需要父 Agent 立即收集结果的任务优先使用 Claude 原生 `Agent`，显式设置 `run_in_background=false`，并在同一轮发出可并行调用。

长时间、彼此独立或适合多个终端持续执行的任务使用 tmux 子 Agent。

默认并发 2～4 个。只有任务天然可以继续独立拆分时才增加并发。

## 模型

每个子 Agent 必须显式指定模型，不继承父会话：

- 默认执行使用 `sonnet`。
- 复杂架构、根因裁决、关键审查使用 `opus`。
- 简单查找、机械核对使用 `haiku`。
- `fable` 仅用于明确需要超长上下文或重型规划的少数任务。

## 写入隔离

只读 Agent 可以共享工作目录。

多个写入型 Agent 不得同时修改同一文件或模块。优先按互不重叠的文件范围分工；无法可靠隔离时，为每个写入任务建立独立 Git worktree。

不要把 worktree 嵌套在主项目 checkout 内。需要了解 DevSpace worktree 的恢复、共享对象数据库等边界时，读取 `~/.agents/references/devspace.md`。

## tmux 执行

一个父任务只创建一个 session，每个子 Agent 使用独立 window 或 pane。session 使用：

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

## 验收与清理

父 Agent 必须读取子 Agent 的实际输出和代码变更，自行检查、验证并形成最终结论；子 Agent 的“已完成”自述不是成功证据。

测试或检查发现的问题仍按当前项目的 Git 原子提交规则处理。

任务结束后关闭对应 tmux session，不得遗留空闲 Claude 进程或后台会话。
