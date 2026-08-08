# Akira Skills

Akira 自研 Agent Skills 的独立源码仓库。

本仓库只维护我们自己的可复用 Skill。Akira Lattice 通过 Git submodule 固定本仓库的具体 commit，再由 skills CLI 安装到各 Agent 运行时。Matt Pocock 的 Skills 使用独立的 `Akira-TL/matt-skills` fork，不与本仓库混合。

## 结构

```text
skills/
├── engineering/      # 工程开发与 Agent 编排
├── productivity/     # 文档、浏览器等通用生产力能力
├── in-progress/      # 尚未稳定的 Skill
├── deprecated/       # 已弃用但保留迁移说明的 Skill
├── docs/             # 面向使用者的 Skill 文档
├── scripts/          # 本仓库机械 Guard
└── AGENTS.md         # 本仓库维护规则
```

每个正式 Skill 的 runtime source 位于 `<category>/<skill-name>/SKILL.md`。可选的 reference 与 `SKILL.md` 同目录保存，并由正文显式引用。

## 当前 Skills

- `engineering/devspace-orchestration`：DevSpace 多 Agent、tmux 与 Git worktree 编排。
- `productivity/general-word-document-generation`：Word 原生语义的正式 DOCX 生成与修订。
- `productivity/visible-browser-form-automation`：WSL 控制用户可见 Windows Chrome 的表单自动化。

对应用户文档位于 `docs/<category>/<skill-name>.md`。

## 安装

直接从 GitHub 安装指定 Skill：

```bash
npx skills add Akira-TL/skills --skill devspace-orchestration --agent '*' -g -y
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

使用仓库自己的 Guard：

```bash
uv run scripts/guard.py check
```

Guard 负责检查 Skill 目录名、frontmatter、重复名称、基础仓库结构，以及稳定 Skill 与 `docs/<category>/<skill-name>.md` 的一一映射。

## 与 Akira Lattice 的关系

Akira Lattice 不再保存本仓库 Skill 的第二份正文，只通过 `skills/akira` Git submodule 记录本仓库 commit。修改 Skill 时先在本仓库完成并提交，再回到 Lattice 更新 submodule pointer。
