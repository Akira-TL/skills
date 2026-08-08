# DevSpace 多 Agent 编排

`devspace-orchestration` 用于在 DevSpace 中安全地组织并行子 Agent、tmux 长任务和 Git worktree 隔离。

它解决的是“如何编排多个执行者”，而不是要求所有任务都使用多 Agent。单 Agent 可以清晰完成时应直接执行。

## 适用场景

- 多个子任务可以独立并行并由父 Agent 汇总。
- 长任务适合在 tmux 中持续运行。
- 多个写入型 Agent 需要隔离文件范围或使用独立 worktree。
- 需要明确记录每个子 Agent 的模型、工作目录、任务边界和预期输出。

## 核心原则

短时并行优先 Claude 原生 Agent；长时间、终端化任务使用 tmux。默认执行模型为 Sonnet，复杂独立判断使用 Opus，机械查找使用 Haiku。

只读 Agent 可以共享工作目录；写入型 Agent 不得同时修改相同文件或模块。无法安全按文件范围隔离时使用独立 worktree。

父 Agent 负责最终验收，必须读取实际输出和代码变更，不能把子 Agent 的自述当作成功证据。任务结束后清理对应 tmux session。

## 与 Akira Lattice 的关系

Skill runtime source 位于：

```text
engineering/devspace-orchestration/SKILL.md
```

Akira Lattice 的全局 `core/AGENTS.md` 只保留“什么时候考虑多 Agent、默认模型和写入隔离”等长期策略；具体编排步骤由本 Skill 按需加载。

DevSpace 的 `workspaceId`、linked worktree 恢复方式等低频工具事实继续由 Lattice 的 `core/references/devspace.md` 管理，避免把 workflow 和运行环境 reference 混为一体。

## 安装

从当前仓库安装：

```bash
npx skills add . --skill devspace-orchestration --agent '*' -g -y
```

也可以直接从 GitHub 安装：

```bash
npx skills add Akira-TL/skills --skill devspace-orchestration --agent '*' -g -y
```
