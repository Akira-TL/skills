# Akira 能力目录

本文件是 `akira` Router 的 first-party 能力映射表。它只回答四件事：当前需求对应哪个入口 Package、该 Package 的 Primary Router / Owner 是谁、当前应使用什么 source mode，以及默认安装到用户级还是项目级 Target。

Package 的完整依赖闭包不在这里维护。所有直接依赖只写入 owning Package 的 `skiloom-package.toml`，递归解析由 Skiloom resolver 完成。

## 使用规则

- 当前会话已经具备所需能力时直接复用，不因为 Catalog 中存在其他能力而扩张 Target。
- 需要新增能力时只选择最小入口 Package coordinate，并使用本表登记的默认 scope；不得为了方便把项目级产品降级安装到用户级 Target。
- 当前 first-party 仓尚未完成统一 Release 发布，因此使用显式 Git `main` source：`--git main`。未来切到正式 Release 后只修改 source policy，不把 dependency closure 搬回 Catalog。
- 安装、更新、移除、同步、修复与诊断全部交给 Skiloom；具体执行契约见 [`INSTALLATION.md`](INSTALLATION.md)。
- first-party 不足时再读取 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md)。

## Akira 通用能力

Repository coordinate：`akira-tl/skills`

| 需求 | 入口 Package coordinate | Owner | 默认 scope | 默认策略 |
| --- | --- | --- | --- | --- |
| 能力选择、跨产品路由与内置 Guard | `akira-tl/skills/akira` | `akira` | `user` | 基础能力 |
| 动态/认证网页与浏览器控制 | `akira-tl/skills/browser-access` | `browser-access` | `user` | 基础能力 |
| Word / DOCX 生成与编辑 | `akira-tl/skills/general-word-document-generation` | `general-word-document-generation` | `user` | 按需 |
| 科研/学术 PPT | `akira-tl/skills/scientific-presentation-authoring` | `scientific-presentation-authoring` | `user` | 按需 |
| 已拆分工作的 Agent 执行适配 | `akira-tl/skills/agent-orchestration` | `agent-orchestration` | `user` | 按需 |

`scientific-presentation-authoring` 可按需调用 `humanizer-zh` 做额外中文语言 QA；它不是强制 dependency，也不是交付门禁。默认候选与窄调用边界见 External Sources。

## Matt Engineering

- Repository coordinate：`akira-tl/matt-skills`
- Status：available
- 入口 Package：`akira-tl/matt-skills/ask-akira`
- Primary Router：`ask-akira`
- Source mode：Git `main`
- Default scope：`workspace`

持续软件工程项目只选择 `ask-akira` 作为入口。必须在目标项目根目录使用 `--scope workspace`；不得因当前项目尚未初始化 Skill Target 而安装到用户级 Target。`ask-matt`、TDD、代码审查、诊断、设计与其他 Matt Skills 的安装闭包由 `skiloom-package.toml` 自动解析，不在这里枚举。

Parallel 系列中，`parallel-execution` 已通过现有依赖图进入标准工程闭包；需要主 Agent 发布/协调 Parallel Task 与 Gate 时，再按真实任务额外选择：

- `akira-tl/matt-skills/parallel-coordinator`

## Akira Research

Repository coordinate：`akira-tl/akira-research-skills`

### Research series

- Status：available
- 入口 Package：`akira-tl/akira-research-skills/akira-research`
- Primary Router：`akira-research`
- Source mode：Git `main`
- Default scope：`workspace`

用于持续科研项目、研究执行、分析、解释与科学传播。必须安装到当前科研项目的 workspace Target。Research series 的专业 Skill 与共享能力由 `akira-research` 的 Package dependency graph 自动闭合。

### Review series

- Status：available
- 入口 Package：`akira-tl/akira-research-skills/akira-review`
- Primary Router：`akira-review`
- Source mode：Git `main`
- Default scope：`workspace`

用于导师式学术评议、独立同行评议、创新性核验与修回再审。必须安装到当前评议/科研项目的 workspace Target。Review 与 Research 是平级入口；安装其中一个不会因为同仓而自动把另一个升级为 direct requirement。

## Akira Knowledge

- Repository coordinate：`akira-tl/akira-knowledge-skills`
- Status：available
- 入口 Package：`akira-tl/akira-knowledge-skills/akira-knowledge`
- Primary Router：`akira-knowledge`
- Source mode：Git `main`
- Default scope：`workspace`

`akira-knowledge` 是项目级 / Vault 级长期知识工作流，必须从目标知识项目或 Obsidian Vault 对应工作目录安装到 `workspace` Target；不得进入用户级 `~/.agents/skills`。`akira-knowledge` 负责长期知识管理入口；`knowledge-capture`、`knowledge-curate`、`knowledge-maintain` 与 `knowledge-retrieve` 的闭包由 Skiloom dependency graph 自动解析。

## Akira Video

- Repository coordinate：`akira-tl/akira-video-skills`
- Status：available
- 入口 Package：`akira-tl/akira-video-skills/akira-video`
- Primary Router：`akira-video`
- Source mode：Git `main`
- Default scope：`workspace`

`akira-video` 是项目级 AI 视频制作工作流。它维护项目根目录的 `VIDEO.md` 与 `video/` 制作内容，按当前任务路由视频脚本、复用素材、镜头、一次性生成包、审片和整片后期；小说、章节或其他上游内容仍由原 owning Skill / 项目文件拥有。完整核心闭包由 `akira-video` 的 Package dependency graph 自动解析，广告等可选领域能力按真实项目需要单独增加。

## 快速选择

| 当前需求 | 入口 Package | scope |
| --- | --- | --- |
| 能力路由 | `akira-tl/skills/akira` | `user` |
| 浏览器 | `akira-tl/skills/browser-access` | `user` |
| Word / DOCX | `akira-tl/skills/general-word-document-generation` | `user` |
| 科研/学术 PPT | `akira-tl/skills/scientific-presentation-authoring` | `user` |
| Guard | `akira-tl/skills/akira`（内置） | `user` |
| Agent 执行适配 | `akira-tl/skills/agent-orchestration` | `user` |
| 软件工程 | `akira-tl/matt-skills/ask-akira` | `workspace` |
| Parallel 主协调 | `akira-tl/matt-skills/parallel-coordinator` | `workspace` |
| 科研项目 | `akira-tl/akira-research-skills/akira-research` | `workspace` |
| 学术评议 | `akira-tl/akira-research-skills/akira-review` | `workspace` |
| 长期知识管理 | `akira-tl/akira-knowledge-skills/akira-knowledge` | `workspace` |
| AI 视频制作 | `akira-tl/akira-video-skills/akira-video` | `workspace` |

## 生命周期边界

- Catalog 只选择入口 Package，不手写完整 Skill 列表。
- `skiloom-package.toml` 是 Package dependency 的唯一事实来源。
- Skiloom Registry / accepted Target state 是安装状态的唯一事实来源。
- 不读取或写入旧 `~/.agents/akira-skills.json` 作为安装状态。
- 不通过旧 `~/.agents/sources/`、目录扫描或软链接存在性替代 Skiloom 状态判断。
- `planned`、不兼容或无法通过 Skiloom admission 的候选保持 blocker，不使用旧安装器绕过。
