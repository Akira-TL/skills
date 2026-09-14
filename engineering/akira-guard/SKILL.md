---
name: akira-guard
summary: 理解、配置与排查 Akira Guard，并在需要时选择统一的提交、架构、Skill 与收尾检查入口。
description: 用于配置、扩展或排查 Akira Guard，或需要判断 Guard 各命令与轻量提交检查、关键修改验证之间边界的任务。普通开发中已经明确知道具体 `~/.agents/skills/akira-guard/scripts/guard.py` 命令时直接调用，不要为了执行已知命令额外加载本 Skill。
---

# Akira Guard

Akira Guard 是跨项目的机械检查与 Git 提交入口。本 Skill 同时拥有 Guard 的通用执行实现与使用语义；安装后统一通过 `~/.agents/skills/akira-guard/scripts/guard.py` 调用。Lattice 只保留自身静态配置与仓库拓扑检查，不再作为跨项目 Git Guard 的实现 owner。

## 先确认当前能力

需要了解命令、参数或排查行为时，先读取实际 CLI：

```bash
uv run ~/.agents/skills/akira-guard/scripts/guard.py --help
uv run ~/.agents/skills/akira-guard/scripts/guard.py <command> --help
```

以当前 CLI 与实现为事实来源，不在 Skill 中维护容易过期的完整参数表。

## 普通提交

已完成一个明确修改目的后：

1. 检查 diff ownership，只暂存当前原子修改。
2. 使用 `uv run ~/.agents/skills/akira-guard/scripts/guard.py commit -m '<message>'` 正式提交。
3. Guard 负责提交入口中的轻量、确定性机械门禁；不要因为“最低检查”自行扩张为全项目 lint、typecheck、build 或 test suite。

普通开发中如果已经知道要调用 `commit`，直接调用即可，不要求先经过本 Skill。

## 检查分层

**提交级最低检查**应当快速、确定，并只针对即将提交的内容。语法完整性、提交格式、架构阈值等适合由 Guard 在提交入口机械执行。

**风险驱动验证（risk-based validation）**只在大型、关键或高风险修改时追加。根据实际改动选择 targeted test、类型检查、构建、schema/migration validator、项目专属 validator 或其他能够覆盖主要失败模式的检查，不机械运行与本次修改无关的全套命令。

最终验收需要组合机械检查和 Git/worktree 概览时，使用 Guard 当前提供的 `check` 能力；项目自身测试与 validator 仍由项目约束决定，Guard 不替代它们。

## 边界

- Guard 是执行层，不负责判断 diff ownership、科研语义、业务正确性或用户是否接受实现。
- Skill 同时携带 Guard 通用执行脚本，但不会通过额外中间层包裹每次命令；Agent 已知命令时直接调用脚本。
- 不为使用 Guard 安装全局 Git Hook，也不抢占项目已有 Husky、pre-commit、lefthook 或其他 Git Hook 的所有权。
- 修改 Guard 本身时，把实现、测试与文档按独立修改目的分阶段提交；Guard 的机械规则与 Skill 的说明保持单一事实来源，不复制实现细节。
