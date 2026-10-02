# akira

`akira` 是 Akira 通用能力 Router。它只负责回答“当前任务缺什么能力、应选择哪个入口 Package”，不再实现 Skill 生命周期。

## 主要路由

- 软件工程：入口 `akira-tl/matt-skills/ask-akira`，Primary Router 为 `ask-akira`，默认安装到当前项目 `workspace` Target。
- Research series：入口 `akira-tl/akira-research-skills/akira-research`，默认安装到当前科研项目 `workspace` Target。
- Review series：入口 `akira-tl/akira-research-skills/akira-review`，默认安装到当前评议/科研项目 `workspace` Target。
- Knowledge：入口 `akira-tl/akira-knowledge-skills/akira-knowledge`，当前已 available，默认安装到目标知识项目 / Vault 对应工作目录的 `workspace` Target。
- AI 视频制作：入口 `akira-tl/akira-video-skills/akira-video`，默认安装到当前视频项目的 `workspace` Target；入口负责定位 / 初始化 `video/Vxxx_*` 后交给 `video-production`，具体制作结构继续由 Video 产品仓维护。
- 浏览器、Word、科研/学术 PPT、Guard、Agent 执行适配：选择 `akira-tl/skills/<skill-name>` 单一 Package。
- 外部能力：先通过 Skiloom discovery 获取候选，再按来源、副作用与数据边界审计。

## 生命周期边界

`routing/akira/references/CATALOG.md` 只维护需求 → 入口 Package coordinate / Owner / source mode 的映射；Package 依赖只维护在 `skiloom-package.toml`。

`akira` 的生命周期动作要求 Skiloom CLI，并在可用时加载 Skiloom Router / specialist。当前 Skiloom Router 由 Lattice 以显式 Git source 先行 bootstrap；这一前置条件记录在 `routing/akira/DEPENDENCIES.md`，不使用会在 fresh Target 触发 Release resolution 失败的跨仓 `*` dependency。

当前 Target 状态按 Catalog 登记的默认 scope 查询：

```text
skiloom status --scope <user|workspace> --json
```

Matt、Research、Review、Knowledge 与 Video 的 `workspace` scope 必须从目标项目 / Vault 对应工作目录执行；不得因为用户级已经安装同名 Package 就跳过项目级安装。

获取。不得再用旧 `~/.agents/akira-skills.json`、`~/.agents/sources/` 或软链接存在性推断安装事实。

当前 first-party 仓暂以 Git `main` 作为 source mode。典型安装流程：

```text
skiloom install <coordinate> --git main --scope <catalog-scope> --plan --json
skiloom install <coordinate> --git main --scope <catalog-scope> --yes --json
```

第一条只生成 Candidate plan；第二条要求用户已经明确授权该状态变化。dependency closure、exact source、Store、Target ownership 与 reconciliation 全部由 Skiloom 负责。

Akira 不再维护自己的 Git checkout、symlink Registry、private manifest、dependency solver 或 fallback installer。

## 最小安装原则

Router 默认先复用当前会话已有能力。需要新增能力时只选择当前任务的最小入口 Package；Research、Review、Matt、Knowledge、Video 之间不会因为都由 Akira 维护而自动相互安装。

完整规则见：

- `routing/akira/references/CATALOG.md`
- `routing/akira/references/INSTALLATION.md`
- `routing/akira/references/EXTERNAL-SOURCES.md`
