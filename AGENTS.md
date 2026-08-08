# Repository instructions

本仓库是 Akira 自研 Agent Skills 的独立 canonical source。它只维护我们自己的 Skill，不包含 Matt Pocock 或其他第三方 Skill 的正文。

## 目录与所有权

- 稳定 Skill 放在 `<category>/<skill-name>/`，例如 `engineering/`、`productivity/`。
- 尚未稳定的 Skill 放在 `in-progress/`；弃用 Skill 放在 `deprecated/`，不得无迁移说明地直接删除已发布名称。
- 每个 Skill 只有一个 canonical `SKILL.md`；长分支说明可放同目录 sibling reference，并由 `SKILL.md` 显式引用。
- 面向使用者的说明放在 `docs/<category>/<skill-name>.md`。文档解释用途、边界和安装方式，不复制整个运行时 Prompt。
- 不把 Matt skills 或其他第三方 Skill 正文复制进本仓库；第三方来源由 Akira Lattice 的独立 submodule 管理。

## Skill 编写

- Skill 目录名与 frontmatter `name` 使用 lowercase kebab-case 且必须一致。
- 在编写正文前先确定 Skill 是 user-invoked 还是 model-invoked；只保留清晰且可判定的触发条件。
- 多步骤流程写成可检查的顺序；稳定规则靠近其约束行为，低频或分支材料移入 reference。
- 同一规则只保留一个 source of truth，清理重复、陈旧内容和无操作意义的泛化建议。

## 检查与提交

- 本仓库不维护独立 Guard；机械检查与正式 Git 提交统一使用 Akira Lattice 投射到 `~/.agents/scripts/` 的全局入口，例如 `uv run ~/.agents/scripts/guard.py check`。
- 修改稳定 Skill 时同步修改对应 `docs/` 文档；发布行为变化时记录到仓库变更说明（若当前维护）。
- Git 原子提交、diff ownership 与提交信息继续遵守加载到 Agent 的全局 Git 规则；不得因为本仓库独立而降低提交标准。
