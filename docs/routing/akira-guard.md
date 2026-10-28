# Akira Guard

Akira Guard 现在是必装 `akira` Package 的内置执行能力，不再单独发布为 `akira-guard` Skill Package。

## 使用方式

canonical implementation 随 `akira` 发布：

```text
routing/akira/scripts/guard.py
routing/akira/scripts/staged_syntax.py
```

安装后的统一入口：

```bash
uv run ~/.agents/skills/akira/scripts/guard.py <command>
```

普通开发中已经知道具体 Guard 命令时可以直接调用，不需要额外加载独立 Guard Skill。需要理解 Guard 能力、选择检查层级、配置或排查行为时，读取 `akira` 的 `references/GUARD.md`。

## 检查层级

普通原子提交只承担快速、确定性的提交级最低检查，不默认扩张为全项目 lint、类型检查、构建或完整测试。

大型、关键或高风险修改根据实际失败模式追加 targeted test、类型检查、构建、schema/migration validator 或项目专属检查。最终收尾可使用 Guard 的组合检查能力，同时继续遵守项目自己的验收要求。

## 单行代码长度设置

提交默认阻止新增或修改的代码行超过 120 字符，错误中给出文件、行号与实际长度。未改动的历史长行不阻塞提交；全目录检查仍会报告历史问题。

在目标项目运行以下命令可持久设置该项目的上限：

```bash
git config akira.guardMaxLineLength 120
```

增加 `--global` 可设置所有项目的用户默认值。单次调用可使用 `--max-line-length`：

```bash
uv run ~/.agents/skills/akira/scripts/guard.py architecture --staged --max-line-length 120
```

命令行参数优先于 Git 配置，`commit` 和 `check` 也支持此参数。计数方式、文件范围和重命名行为见 [`GUARD.md`](../../routing/akira/references/GUARD.md#单行代码长度)。

## Skiloom Store 边界

Linux 上 Skiloom 可以把 managed projection 以 symlink 指向 Package Store payload。Guard 在导入 sibling Python 模块前关闭 bytecode 写入，避免 `__pycache__` / `.pyc` 污染 Store。

## 生命周期

Guard 随 `akira-tl/skills/akira` 一起安装、更新、同步和修复；没有独立 Package coordinate、独立 direct requirement 或独立生命周期。

Lattice bootstrap 只需要安装 `akira`，即可获得 Guard。
