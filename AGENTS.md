# Repository instructions

本仓库是 Akira 通用 Skills 与跨仓库能力 Router 的 canonical source。它维护跨领域可复用能力，不再承载完整 Research 产品，也不复制 Matt 工程 Skill 正文。

## 目录与所有权

- `routing/` 保存跨仓库 Router；当前 `akira` 负责根据项目用途选择最小 Skill / 产品仓。
- `productivity/` 保存跨领域交付能力，例如浏览器、Word、科研/学术 PPT。
- `engineering/` 只保存真正跨项目的基础设施能力，例如 Akira Guard 使用语义与 harness-agnostic Agent 编排；Matt 的工程方法、`ask-akira` 与 Parallel 系列属于 `Akira-TL/matt-skills` fork。
- 完整科研工作流属于独立 `akira-research-skills`；未来 Knowledge 等高内聚产品族也应独立成仓。
- 尚未稳定的本仓通用 Skill 放在 `in-progress/`；弃用 Skill 放在 `deprecated/`，不得无迁移说明地直接删除已发布名称。
- 每个稳定 Skill 只有一个 canonical `SKILL.md`；人类文档放在 `docs/<category>/<skill-name>.md`。

## 安装边界

本仓存在不等于默认安装本仓全部 Skill。Akira Lattice 只把真实需要的 Skill 安装到 `~/.agents/sources/` 并注册到机器级 `~/.agents/skills/`；这两层是 Akira 管理的唯一 Skill source 与机器级注册层。ForgeRelay、Claude Code、Codex 等执行器若需要持久暴露某个 Skill，由执行器自己在其 Skill 目录建立指向 `~/.agents/skills/<name>` 的软链接；共享安装器不得写入执行器目录，也不得为执行器维护第二份 source checkout。

Router 的受管产品状态只在 `routing/akira/references/CATALOG.md` 维护。未发布、planned 或 unavailable 的仓库不得生成伪造的可执行安装命令。

## Skill 编写

- Skill 目录名与 frontmatter `name` 使用 lowercase kebab-case 且必须一致。
- 编写正文前先确定 user-invoked 或 model-invoked；只保留清晰可判定的触发条件。
- 多步骤流程写成可检查顺序；分支或低频材料放 sibling reference，并由 `SKILL.md` 显式引用。
- 同一规则只保留一个 source of truth；产品仓正文不为了“方便 Router”复制回本仓。

## 检查与提交

- 本仓不维护第二份 Guard；机械检查与正式 Git 提交统一使用 Akira Lattice 投射到 `~/.agents/scripts/` 的入口。
- 稳定 Skill 行为变化同步对应 `docs/`。
- Git 原子提交、diff ownership 与提交信息继续遵守全局 Git 规则。
