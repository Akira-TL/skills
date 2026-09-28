# Akira Guard

Akira Guard 是 `akira` 必装 Package 内置的跨项目机械检查与 Git 提交入口，不再是独立 Skill Package。其实现随 `akira` 一起安装，统一通过：

```text
~/.agents/skills/akira/scripts/guard.py
```

调用。

## 先确认当前能力

需要了解命令、参数或排查行为时，以实际 CLI 为事实来源：

```bash
uv run ~/.agents/skills/akira/scripts/guard.py --help
uv run ~/.agents/skills/akira/scripts/guard.py <command> --help
```

## 普通提交

已完成一个明确修改目的后：

1. 检查 diff ownership，只暂存当前原子修改。
2. 使用 `uv run ~/.agents/skills/akira/scripts/guard.py commit -m '<message>'` 正式提交。
3. Guard 只负责提交入口中的轻量、确定性机械门禁；不要因为“最低检查”自行扩张为全项目 lint、typecheck、build 或 test suite。

普通开发中如果已经知道具体 Guard 命令，直接调用脚本，不需要额外加载第二个 Skill。

## 检查分层

**提交级最低检查**应快速、确定，并只针对即将提交的内容。语法完整性、提交格式、架构阈值等适合由 Guard 在提交入口机械执行。

**风险驱动验证（risk-based validation）**只在大型、关键或高风险修改时追加。根据实际改动选择 targeted test、类型检查、构建、schema/migration validator、项目专属 validator 或其他能够覆盖主要失败模式的检查。

最终验收需要组合机械检查和 Git/worktree 概览时，使用 Guard 的 `check` 能力；项目自身测试与 validator 仍由项目约束决定。

## Skiloom Store 边界

Skiloom 在 Linux 上可以用 symlink materialization 把 managed projection 指向 Package Store payload。Guard 的 Python 入口在导入 sibling 模块前设置 `sys.dont_write_bytecode = True`，避免 `__pycache__` / `.pyc` 反向污染 Store。

Guard 自身不得把运行时缓存写回 Skill Package。

## 边界

- Guard 是执行层，不负责判断 diff ownership、科研语义、业务正确性或用户是否接受实现。
- Guard 随 `akira` Package 发布，不建立独立 Package、独立 Registry requirement 或第二套生命周期。
- 不为使用 Guard 安装全局 Git Hook，也不抢占项目已有 Husky、pre-commit、lefthook 或其他 Git Hook 的所有权。
- 修改 Guard 时，把实现、测试与文档按独立修改目的提交；机械规则与说明保持单一事实来源。
