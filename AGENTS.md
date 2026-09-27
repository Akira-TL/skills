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

`routing/akira/` 只拥有能力选择与跨产品路由，不再拥有独立 Skill 生命周期实现。Package discovery、dependency resolution、source resolution、Registry / Store / Target、安装、更新、移除、同步、修复与恢复全部交给 Skiloom public CLI；本仓不得重新建立 Git checkout + symlink + private manifest 的第二写入路径。

`akira` 的生命周期动作要求 Skiloom CLI；当前 Skiloom first-party 仓尚无可供默认 Release resolver 使用的正式 Release，因此这一前置条件记录在 `routing/akira/DEPENDENCIES.md`，不伪装成会在 fresh Target 失败的跨仓 `*` Package dependency。Lattice 根安装器先通过公开 `skiloom install akira-tl/skiloom/skiloom --git main` 显式建立 Skiloom Router / specialist direct requirement，再 bootstrap `akira`、`browser-access` 与 `akira-guard`；当前 bare `skiloom bootstrap` 因上游尚无 GitHub Release 不能用于 fresh Target。

Router 的 first-party 能力映射只在 `routing/akira/references/CATALOG.md` 维护。Catalog 选择入口 Package coordinate，不复制 `skiloom-package.toml` 中的依赖闭包；不兼容、planned 或无法通过 Skiloom admission 的候选不得生成绕过标准的安装路径。

## Skill 编写

- Skill 目录名与 frontmatter `name` 使用 lowercase kebab-case 且必须一致。
- 每个 Skill 包维护 `skiloom-package.toml`，仓库级发现范围由根目录 `skiloom-repo.toml` 统一定义；canonical `SKILL.md` 只使用标准 Agent Skill frontmatter，执行器专属调用策略留在执行器自己的 metadata 文件中。
- 编写正文前先确定 user-invoked 或 model-invoked；只保留清晰可判定的触发条件。
- 多步骤流程写成可检查顺序；分支或低频材料放 sibling reference，并由 `SKILL.md` 显式引用。
- 同一规则只保留一个 source of truth；产品仓正文不为了“方便 Router”复制回本仓。

## 检查与提交

- 修改 Skill 或 Skiloom metadata 后，从本仓根目录运行 `skiloom validate . --json`，确保仓库发现规则、标准 frontmatter 与 Package metadata 全部可被公开 CLI 接受。
- `engineering/akira-guard/` 是跨项目 Guard 的 canonical owner，通用 Git 提交与机械检查脚本随 Skill 发布；Lattice 只保留自身配置/仓库拓扑检查。
- 稳定 Skill 行为变化同步对应 `docs/`。
- Git 原子提交、diff ownership 与提交信息继续遵守全局 Git 规则。
