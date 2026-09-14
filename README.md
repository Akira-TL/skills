# Akira Skills

Akira 的通用 Agent Skills 与能力 Router 仓库。

本仓库不是所有 Akira 产品能力的集合。高内聚产品族独立维护：科研工作流位于 `akira-research-skills`，软件工程主流程位于 `Akira-TL/matt-skills` fork；本仓库保留跨领域通用能力和 `akira` Router，让项目按真实用途安装最小 Skill 集合。

## 结构

```text
routing/
└── akira/                         # 跨仓库能力 Router
    ├── scripts/                   # Router 自带 Skill 安装/诊断能力
    └── tests/                     # 安装能力定向测试
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
- **Matt Engineering**：`Akira-TL/matt-skills`。Akira 自主维护的 Matt 系列工程方法，以及 `ask-akira`、`parallel-coordinator`、`parallel-execution` 扩展。
- **Akira Research**：`Akira-TL/akira-research-skills`。Research Tree、Literature、Design、Study、Data、Analysis、Interpretation、Communication 与 `research.sqlite` provenance。
- **Akira Knowledge**：尚未建立；真正开始知识系统后再单独成仓，不提前维护空实现。

`routing/akira/references/CATALOG.md` 是 Router 使用的受管产品目录。

## 安装

Skill 安装能力由 `routing/akira/` 自己维护。Lattice 根 `install.sh` 只通过云端临时 checkout 调用本 Skill 的安装器 bootstrap `akira` 与 `browser-access`；Router 已可用后，其他能力均由 Agent 在确认能力缺口并获得用户授权时调用本 Skill 自带脚本安装。

查看远端仓当前可用 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py inspect https://github.com/Akira-TL/skills.git
```

机器级注册表只缺单一通用能力时，只安装对应 Skill，例如：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill browser-access
```

专业产品按真实任务安装到机器级 `~/.agents/skills`。软件工程任务由 `akira` Router 推荐 Akira Matt Engineering；科研任务由 Router 推荐 Research suite。Router 在安装前说明来源、用途与范围并请求用户明确同意。

`~/.agents/sources/` 与 `~/.agents/skills/` 是 `akira` Skill 安装器管理的唯一 Skill source 与机器级注册层。具体执行器需要某个已安装 Skill 时，由执行器自己的机制引用 `~/.agents/skills/<name>`；安装器不写执行器目录，也不为执行器维护第二份 source checkout。

## 检查

本仓库不复制 Guard 实现。维护环境使用 Akira Lattice 的统一入口：

```bash
uv run ~/.agents/scripts/guard.py skills .
```

稳定 Skill 修改需同步对应 `docs/<category>/<skill-name>.md`。
