# Repository instructions

本仓库是 Akira 通用 Skills 与跨仓库能力 Router 的 canonical source。它维护跨领域可复用能力，不再承载完整 Research 产品，也不复制 Matt 工程 Skill 正文。

## 目录与所有权

- `routing/` 保存跨仓库 Router；当前 `akira` 负责根据项目用途选择最小 Skill / 产品仓。
- `productivity/` 保存跨领域交付能力，例如浏览器、Word、科研/学术 PPT。
- `engineering/` 只保存真正跨项目的基础设施能力，例如 Akira Guard 使用语义与 harness-agnostic Agent 编排；Matt 的工程方法、`ask-akira` 与 Parallel 系列属于 Akira 自主维护的 `Akira-TL/matt-skills`。
- 完整科研工作流属于独立 `akira-research-skills`；Akira Knowledge 已独立到 `akira-knowledge-skills`，当前仓库只维护其能力发现状态，不复制 Knowledge 产品正文。
- 尚未稳定的本仓通用 Skill 放在 `in-progress/`；弃用 Skill 放在 `deprecated/`，不得无迁移说明地直接删除已发布名称。
- 每个稳定 Skill 只有一个 canonical `SKILL.md`；人类文档放在 `docs/<category>/<skill-name>.md`。

## 安装边界

Skill 发现与机器级安装由 `routing/akira/` 自己拥有：Router 决定是否需要新增能力，`routing/akira/scripts/` 机械执行远端 Git checkout、机器级注册、更新、删除与诊断。Lattice 根仓不实现通用 Skill 生命周期，只允许 `install.sh` 从云端临时 checkout 调用本 Skill 的安装器，bootstrap `akira`、`browser-access` 与 `akira-guard` 三个基础 Skill。

本仓存在不等于默认安装本仓全部 Skill。真实需要的 Skill 才进入 `~/.agents/sources/` 并注册到 `~/.agents/skills/`；具体执行器若需要持久暴露某个 Skill，由执行器自己的机制引用机器级注册项。安装脚本只管理 Akira 机器级 source 与注册表。

Router 的受管产品状态只在 `routing/akira/references/CATALOG.md` 维护。未发布、planned 或 unavailable 的仓库不得生成伪造的可执行安装命令。

## Skill 编写

- Skill 目录名与 frontmatter `name` 使用 lowercase kebab-case 且必须一致。
- 编写正文前先确定 user-invoked 或 model-invoked；只保留清晰可判定的触发条件。
- 多步骤流程写成可检查顺序；分支或低频材料放 sibling reference，并由 `SKILL.md` 显式引用。
- 同一规则只保留一个 source of truth；产品仓正文不为了“方便 Router”复制回本仓。

## 检查与提交

- `engineering/akira-guard/` 是跨项目 Guard 的 canonical owner，通用 Git 提交与机械检查脚本随 Skill 发布；Lattice 只保留自身配置/仓库拓扑检查。
- 稳定 Skill 行为变化同步对应 `docs/`。
- Git 原子提交、diff ownership 与提交信息继续遵守全局 Git 规则。
