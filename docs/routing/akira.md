# akira

`akira` 是 Akira 通用能力 Router。它只负责回答“当前任务缺什么能力、应选择哪个入口 Package”，不再实现 Skill 生命周期。

## 主要路由

- 软件工程：入口 `akira-tl/matt-skills/ask-akira`，Primary Router 为 `ask-akira`。
- Research series：入口 `akira-tl/akira-research-skills/akira-research`。
- Review series：入口 `akira-tl/akira-research-skills/akira-review`。
- Knowledge：入口 `akira-tl/akira-knowledge-skills/akira-knowledge`，当前已 available。
- 浏览器、Word、科研/学术 PPT、Guard、Agent 执行适配：选择 `akira-tl/skills/<skill-name>` 单一 Package。
- 外部能力：先通过 Skiloom discovery 获取候选，再按来源、副作用与数据边界审计。

## 生命周期边界

`routing/akira/references/CATALOG.md` 只维护需求 → 入口 Package coordinate / Owner / source mode 的映射；Package 依赖只维护在 `skiloom-package.toml`。

`akira` 自身显式依赖 `akira-tl/skiloom/skiloom`。执行安装、更新、移除、同步、修复与恢复时加载 Skiloom Router / specialist，并只使用公开 `skiloom` CLI。

当前 Target 状态通过：

```text
skiloom status --scope user --json
```

获取。不得再用旧 `~/.agents/akira-skills.json`、`~/.agents/sources/` 或软链接存在性推断安装事实。

当前 first-party 仓暂以 Git `main` 作为 source mode。典型安装流程：

```text
skiloom install <coordinate> --git main --scope user --plan --json
skiloom install <coordinate> --git main --scope user --yes --json
```

第一条只生成 Candidate plan；第二条要求用户已经明确授权该状态变化。dependency closure、exact source、Store、Target ownership 与 reconciliation 全部由 Skiloom 负责。

Akira 不再维护自己的 Git checkout、symlink Registry、private manifest、dependency solver 或 fallback installer。

## 最小安装原则

Router 默认先复用当前会话已有能力。需要新增能力时只选择当前任务的最小入口 Package；Research、Review、Matt、Knowledge 之间不会因为都由 Akira 维护而自动相互安装。

完整规则见：

- `routing/akira/references/CATALOG.md`
- `routing/akira/references/INSTALLATION.md`
- `routing/akira/references/EXTERNAL-SOURCES.md`
