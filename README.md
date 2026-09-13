# Akira Skills

Akira 的通用 Agent Skills 与能力 Router 仓库。

本仓库不是所有 Akira 产品能力的集合。高内聚产品族独立维护：科研工作流位于 `akira-research-skills`，软件工程主流程位于 `Akira-TL/matt-skills` fork；本仓库保留跨领域通用能力和 `akira` Router，让项目按真实用途安装最小 Skill 集合。

## 结构

```text
routing/
└── akira/                         # 跨仓库能力 Router
engineering/
├── akira-guard/                   # Guard 使用语义与排障
└── agent-orchestration/           # harness-agnostic 执行适配
productivity/
├── browser-access/                # 浏览器与人工认证边界
├── general-word-document-generation/
└── scientific-presentation-authoring/
in-progress/                       # 本仓未来仍可使用的实验性通用 Skill
deprecated/                        # 旧名称迁移说明
docs/                              # 与稳定 Skill 一一对应的人类文档
```

## 产品边界

- **通用 Akira Skills**：本仓库。Router、浏览器、Word、学术 PPT、Guard 与通用 Agent 执行适配。
- **Matt Engineering**：`Akira-TL/matt-skills`。Matt 工程方法及本 fork 的 `ask-akira`、`parallel-coordinator`、`parallel-execution` 扩展。
- **Akira Research**：`Akira-TL/akira-research-skills`。Research Tree、Literature、Design、Study、Data、Analysis、Interpretation、Communication 与 `research.sqlite` provenance。
- **Akira Knowledge**：尚未建立；真正开始知识系统后再单独成仓，不提前维护空实现。

`routing/akira/references/CATALOG.md` 是 Router 使用的受管产品目录。

## 安装

查看远端仓当前可用 Skill：

```bash
python3 ~/.agents/scripts/skills.py inspect https://github.com/Akira-TL/skills.git
```

采用 Akira 共享注册表的环境只缺单一通用能力时，只安装对应 Skill，例如：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill browser-access
```

专业产品按真实任务安装到机器级 `~/.agents/skills`。软件工程任务由 `akira` Router 推荐 Matt fork；科研任务由 Router 推荐 Research suite。Router 在安装前说明来源、用途与范围并请求用户明确同意。

机器级注册表只属于 Akira 的共享安装模型，不代表所有执行器都必须采用。执行器可以维护独立 Skill store；此时由执行器自己的机制决定常驻能力、按需能力与 source 布局，不得为了兼容自动建立到 `~/.agents/skills` 的跨 store 适配链接。

## 检查

本仓库不复制 Guard 实现。维护环境使用 Akira Lattice 的统一入口：

```bash
uv run ~/.agents/scripts/guard.py skills .
```

稳定 Skill 修改需同步对应 `docs/<category>/<skill-name>.md`。
