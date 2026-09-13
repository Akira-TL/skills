# Akira Guard

`akira-guard` 用于理解、配置和排查 Akira Lattice 的统一 Guard，以及区分普通提交的轻量机械检查与大型、关键修改所需的额外验证。

## 使用方式

Guard 的 canonical implementation 位于 Akira Lattice：

```text
scripts/guard.py
```

安装后通过全局运行时入口调用：

```bash
uv run ~/.agents/scripts/guard.py <command>
```

普通开发中已经知道具体 Guard 命令时可以直接调用，不需要先读取 `akira-guard` Skill。Skill 主要用于需要理解 Guard 能力、选择检查层级、配置或排查 Guard 行为的场景。

## 检查层级

普通原子提交只承担快速、确定性的提交级最低检查，不默认扩张为全项目 lint、类型检查、构建或完整测试。

大型、关键或高风险修改根据实际失败模式追加 targeted test、类型检查、构建、schema/migration validator 或项目专属检查。最终收尾可使用 Guard 的组合检查能力，同时继续遵守项目自己的验收要求。

## 边界

Guard 不替代 Agent 对 diff ownership、语义正确性和原子提交边界的判断，也不接管项目 Git Hook。Akira Lattice 不要求通过全局 Git Hook 才能使用 Guard。

## 安装

机器级安装只从远端 GitHub source 拉取，并注册到 `~/.agents/skills/`：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill akira-guard
```
