# Akira Guard

`akira-guard` 用于理解、配置和排查跨项目 Akira Guard，以及区分普通提交的轻量机械检查与大型、关键修改所需的额外验证。

## 使用方式

Guard 的 canonical implementation 随 `akira-guard` Skill 发布：

```text
engineering/akira-guard/scripts/guard.py
engineering/akira-guard/scripts/staged_syntax.py
```

安装后通过机器级 Skill 入口调用：

```bash
uv run ~/.agents/skills/akira-guard/scripts/guard.py <command>
```

普通开发中已经知道具体 Guard 命令时可以直接调用，不需要先读取 `akira-guard` Skill。Skill 主要用于需要理解 Guard 能力、选择检查层级、配置或排查 Guard 行为的场景。

## 检查层级

普通原子提交只承担快速、确定性的提交级最低检查，不默认扩张为全项目 lint、类型检查、构建或完整测试。

大型、关键或高风险修改根据实际失败模式追加 targeted test、类型检查、构建、schema/migration validator 或项目专属检查。最终收尾可使用 Guard 的组合检查能力，同时继续遵守项目自己的验收要求。

## 边界

Guard 不替代 Agent 对 diff ownership、语义正确性和原子提交边界的判断，也不接管项目 Git Hook。Akira Lattice 不要求通过全局 Git Hook 才能使用 Guard。

Skiloom 在 Linux 上可以把未转换 Package 以 symlink 投影到 Package Store，因此 Guard 的 Python 入口在导入 sibling 模块前显式关闭 bytecode 写入，避免 `__pycache__` / `.pyc` 反向污染 immutable Store payload。Guard 自身不得把运行时缓存写回 Skill Package。

## 安装

`akira-guard` 是 Lattice 基础 bootstrap Package，入口为 `akira-tl/skills/akira-guard`。根 `install.sh` 与 `akira`、`browser-access` 一起通过 Skiloom public CLI 安装到用户级 Target；后续修复、更新与重装同样只走 Skiloom。
