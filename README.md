# Akira Skills

Akira 自研 Agent Skills 的独立源码仓库。

本仓库只维护我们自己的可复用 Skill。Akira Lattice 通过 Git submodule 固定本仓库的具体 commit，再由 skills CLI 安装到各 Agent 运行时。Matt Pocock 的 Skills 使用独立的 `Akira-TL/matt-skills` fork，不与本仓库混合。

## 结构

```text
skills/
├── research/         # 科研总 Router 与专业科研工作流
├── engineering/      # 工程开发与 Agent 编排
├── productivity/     # 文档、浏览器等通用生产力能力
├── in-progress/      # 尚未稳定的 Skill
├── deprecated/       # 已弃用但保留迁移说明的 Skill
├── docs/             # 面向使用者的 Skill 文档
└── AGENTS.md         # 本仓库维护规则
```

每个正式 Skill 的 runtime source 位于 `<category>/<skill-name>/SKILL.md`。可选的 reference 与 `SKILL.md` 同目录保存，并由正文显式引用。

## 当前 Skills

- `research/akira-research`：科研总 Router；围绕 Research Question、证据、Research Tree 与适用规范，自主路由完整科研工作。
  - `research/research-tree`、`research/research-standards`
  - `research/literature`、`research/literature-access`
  - `research/hypothesis`、`research/design`、`research/study`、`research/data`
  - `research/analysis`、`research/interpretation`、`research/communication`
- `engineering/agent-orchestration`：在当前 Agent harness 确实提供并行执行原语时，将已定义工作单元映射到这些能力；不绑定具体产品，也不是 Parallel 的必选依赖。
- `engineering/akira-guard`：Akira Guard 的使用语义、检查分层与故障排查。
- `productivity/general-word-document-generation`：Word 原生语义的正式 DOCX 生成与修订。
- `productivity/scientific-presentation-authoring`：科研与学术类 PPT 的结构、页面文案和结果页图文编排。
- `productivity/browser-access`：按当前 harness 能力发现并复用可控浏览器，支持持久登录态、动态网页、网络资源解析和表单操作。

对应用户文档位于 `docs/<category>/<skill-name>.md`。

## 安装

直接从 GitHub 安装指定 Skill：

```bash
npx skills add Akira-TL/skills --skill agent-orchestration --agent '*' -g -y
```

查看仓库可安装的 Skill：

```bash
npx skills add Akira-TL/skills --list
```

在本地 checkout 中开发或验证时，也可以使用当前目录：

```bash
npx skills add . --list
```

## 检查

本仓库不维护第二份 Guard。维护环境统一使用 Akira Lattice 安装到 `~/.agents/scripts/` 的全局入口：

```bash
uv run ~/.agents/scripts/guard.py check
```

全局 Guard 根据当前仓库识别并检查 Skill 目录名、frontmatter、重复名称，以及稳定 Skill 与 `docs/<category>/<skill-name>.md` 的一一映射。

## 与 Akira Lattice 的关系

Akira Lattice 不再保存本仓库 Skill 的第二份正文，只通过 `skills/akira` Git submodule 记录本仓库 commit。修改 Skill 时先在本仓库完成并提交，再回到 Lattice 更新 submodule pointer。
