# Akira Skills

Akira 的通用 Agent Skills 与能力 Router 仓库。

本仓库不是所有 Akira 产品能力的集合。高内聚产品族独立维护：科研工作流位于 `akira-research-skills`，软件工程主流程位于 `Akira-TL/matt-skills`，长期知识位于 `akira-knowledge-skills`；本仓库保留跨领域通用能力和 `akira` Router。

## 结构

```text
routing/
└── akira/                         # 跨仓库能力 Router；生命周期交给 Skiloom
engineering/
├── akira-guard/                   # Guard 使用语义与排障
└── agent-orchestration/           # harness-agnostic 执行适配
productivity/
├── browser-access/                # 浏览器与人工认证边界
├── general-word-document-generation/
└── scientific-presentation-authoring/
in-progress/                       # 实验性通用 Skill
deprecated/                        # 旧名称迁移说明
docs/                              # 与稳定 Skill 对应的人类文档
skiloom-repo.toml                  # Skiloom repository discovery
```

## 产品边界

- **通用 Akira Skills**：本仓库。Router、浏览器、Word、学术 PPT、Guard 与 Agent 执行适配。
- **Matt Engineering**：`Akira-TL/matt-skills`，Primary Router 为 `ask-akira`。
- **Akira Research**：`Akira-TL/akira-research-skills`，包含平级的 `akira-research` 与 `akira-review`。
- **Akira Knowledge**：`Akira-TL/akira-knowledge-skills`，Primary Router 为 `akira-knowledge`。

`routing/akira/references/CATALOG.md` 只维护需求 → 入口 Package coordinate / Owner / source mode；依赖闭包由各 Package 的 `skiloom-package.toml` 维护。

## 安装与生命周期

本仓不再维护自有 Skill installer。`akira` Package 依赖 `akira-tl/skiloom/skiloom`，所有 Package discovery、dependency resolution、source resolution、Registry / Store / Target、安装、更新、移除、同步、修复与恢复统一使用 Skiloom public CLI。

当前 first-party 仓使用 Git `main` source mode。示例：

```text
skiloom install akira-tl/skills/browser-access --git main --scope user --plan --json
skiloom install akira-tl/skills/browser-access --git main --scope user --yes --json
```

第一条只生成 Candidate plan；第二条要求用户已经明确授权状态变化。

Lattice 根 `install.sh` 要求 Skiloom CLI 已可用，并通过 Skiloom bootstrap 基础 direct requirements：`akira`、`browser-access`、`akira-guard`。

旧 `~/.agents/akira-skills.json`、`~/.agents/sources/` 与 Git + symlink installer 不再具有 lifecycle authority，也没有 fallback 路径。

## 检查

Skiloom Package 静态验证：

```text
skiloom validate . --json
```

跨项目 Guard 实现由 `engineering/akira-guard/` 自己维护。安装后的 Guard 入口仍为：

```bash
uv run ~/.agents/skills/akira-guard/scripts/guard.py skills .
```

稳定 Skill 修改需同步对应 `docs/<category>/<skill-name>.md`。
