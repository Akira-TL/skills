# Akira 能力目录

本文件是 `akira` Router 的 **first-party 能力注册表**，也是“我们现在有哪些能力、从哪里安装、应该安装单个 Skill 还是完整产品族”的唯一 source of truth。

`akira/SKILL.md` 只负责判断何时需要查能力；具体 Skill 名称、GitHub source、发布状态与安装命令只在这里维护。Router 不从 GitHub 搜索结果、旧会话记忆、本机偶然残留目录或其他文档猜测 first-party 能力。

## 使用规则

出现以下任一情况时读取本文件：

- 当前任务需要尚未可用的能力；
- 用户询问“有什么 Skill / 应该安装什么”；
- 需要决定安装单个通用 Skill，还是完整 Research / Matt 产品族；
- 需要生成准确的 `npx skills` 安装命令；
- 需要确认某个产品当前是 `available`、`planned` 还是不可安装。

如果当前能力已经满足任务，不为“以后可能用到”读取并安装更多产品。外部第三方能力不在本表枚举，统一转到 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md)。

## 安装方式：统一使用软链接

Akira 管理的 Skill 使用 `npx skills` 的默认 **symlink mode**。安装命令不使用 `--copy`；安装完成后必须核验消费目录中的 Skill 是软链接，而不是普通目录或复制副本。

ForgeRelay 的固定布局是：

```text
~/.forgerelay/.agents/skills/<skill>   # npx skills canonical store
~/.forgerelay/skills/<skill>           # ForgeRelay 消费的软链接
```

由于当前 `npx skills` 没有原生 ForgeRelay target，也没有任意目标目录参数，ForgeRelay 安装时以 `~/.forgerelay` 为工作目录，同时指定 `universal` 与 `openclaw` 两个 target。`universal` 建立 canonical store，`openclaw` 的 `skills/` profile 让 CLI 自己创建 `~/.forgerelay/skills/<skill> -> ../.agents/skills/<skill>`。这里借用 `openclaw` 只用于路径 profile，不表示 ForgeRelay 依赖 OpenClaw。

ForgeRelay 安装命令形态：

```bash
cd ~/.forgerelay
npx skills add <source> --skill <skill-name> --agent universal openclaw -y
```

验收至少检查：

```bash
test -L ~/.forgerelay/skills/<skill-name>
readlink ~/.forgerelay/skills/<skill-name>
```

若目标是普通目录，则安装未达到 Akira 运行时契约，应按上述 symlink mode 重装；不要用手工复制目录补救。

## ForgeRelay 常驻基线

Akira Lattice 在 ForgeRelay 中只常驻以下两个 Skill，由根仓安装器通过 `npx skills` 的上述软链接模式管理：

| Skill | 用途 | Source | 状态 |
| --- | --- | --- | --- |
| `akira` | 跨产品能力发现、安装决策与 Router | `Akira-TL/skills` | available |
| `browser-access` | 动态网页、登录态、用户可见浏览器与人工认证边界 | `Akira-TL/skills` | available |

Research、Matt、Word、PPT、Guard Skill、Agent 编排和第三方专业能力都不是常驻基线。

## Akira 通用 Skills

GitHub source：`Akira-TL/skills`

单个能力按需安装使用 `npx skills` 默认软链接模式；不得加入 `--copy`：

```bash
npx skills add Akira-TL/skills --skill <skill-name> --agent '*' -y
```

| Skill | 能力 | 默认状态 | 何时安装 |
| --- | --- | --- | --- |
| `akira` | 能力 Router；决定当前项目还缺什么 | ForgeRelay 常驻 | 不单独重复安装 |
| `browser-access` | 动态/认证网页访问、浏览器控制、登录态复用 | ForgeRelay 常驻 | 非 ForgeRelay 项目缺少该能力时按需安装 |
| `general-word-document-generation` | 正式 Word / DOCX 文档生成与编辑 | 按需 | 当前任务明确需要 DOCX |
| `scientific-presentation-authoring` | 科研/学术 PPT 内容组织与交付 | 按需 | 当前任务明确需要科研或学术演示文稿 |
| `akira-guard` | Akira Guard 的使用语义、排障与边界 | 按需 | 需要理解/诊断 Guard，而不是仅执行已有 Guard 命令 |
| `agent-orchestration` | 把已定义工作单元映射到当前 harness 的 Agent 执行原语 | 按需 | 任务已经拆好，且当前 harness 提供可用的多 Agent / 并行执行原语 |

这些通用 Skill 不拥有 Research 状态机，也不复制 Matt 工程方法论。

## Akira Research

- GitHub source：`Akira-TL/akira-research-skills`
- Status：available
- Primary Router：`akira-research`
- 安装粒度：科研项目需要持续 Research 工作流时，安装完整 suite；不要把 13 个 Research Skill 当作全局常驻能力。

项目级安装使用默认软链接模式；不得加入 `--copy`：

```bash
npx skills add Akira-TL/akira-research-skills --skill '*' --agent '*' -y
```

Research suite 当前能力：

| Skill | 能力 |
| --- | --- |
| `akira-research` | 科研项目总 Router、`research.sqlite` 与整体科研状态 |
| `research-tree` | Research Question、Active Uncertainty、研究分支和科学关系 |
| `literature` | 文献发现、阅读、批判性评估与跨论文证据综合 |
| `literature-access` | DOI/PMID/PMCID/论文页面到可核验全文的获取流程 |
| `research-standards` | 领域规范、报告指南与适用科研标准核验 |
| `hypothesis` | competing explanations、预测和判别性 Hypothesis Set |
| `design` | estimand、sampling、comparison、measurement、controls 与研究设计 |
| `study` | 实际实验/观察/采样/Assay 执行和 deviation provenance |
| `data` | Dataset identity、raw/curated/derived、QC、mapping 与 freeze |
| `analysis` | 统计、生物信息、机器学习、敏感性分析和可重建计算 |
| `interpretation` | Observation、Claim、因果/机制边界与科学解释 |
| `communication` | 研究论文、综述、报告、补充材料与 reviewer response |
| `ngs` | NGS assay-specific QC、reference/database、pipeline 与执行 provenance |

需要其中任一持续科研能力时，默认由 `akira-research` 接管后续路由，而不是让 `akira` 直接执行科研工作。

## Matt Engineering

- GitHub source：`Akira-TL/matt-skills`
- Status：available
- Primary Router：`ask-matt`
- 安装粒度：软件工程项目需要完整工程方法链时安装整个 Matt fork。

项目级安装使用默认软链接模式；不得加入 `--copy`：

```bash
npx skills add Akira-TL/matt-skills --skill '*' --agent '*' -y
```

Matt fork 提供需求澄清、Spec/Ticket、实现、TDD、代码审查、缺陷诊断、重构、工程写作等完整工程能力。Akira 自有增量与 Matt 同仓维护：

| Skill | 能力 |
| --- | --- |
| `ask-akira` | 在 Matt 工程方法上增加 Akira 项目协作与路由 |
| `parallel-coordinator` | 发布和协调 Parallel Task / Gate 工作 |
| `parallel-execution` | Worker 领取、执行、提交和阶段汇报协议 |

这些增量不是第二套工程体系；软件工程安装 Matt fork 后，以 `ask-matt` / `ask-akira` 继续路由。

## Akira Knowledge

- Planned source：`Akira-TL/akira-knowledge-skills`
- Status：planned
- 用途：知识采集、概念关系、长期笔记、知识总结与复习工作流。

当前没有可安装实现。不得生成伪造的安装命令，也不得因为规划存在就把它描述为 available。

## 快速选择表

| 当前需求 | 选择 | 安装策略 |
| --- | --- | --- |
| 动态网页 / 登录态 / 浏览器 | `browser-access` | ForgeRelay 已常驻；其他环境缺少时装单个 Skill |
| Word / DOCX | `general-word-document-generation` | 只装单个 Skill |
| 科研/学术 PPT | `scientific-presentation-authoring` | 只装单个 Skill |
| Guard 语义/排障 | `akira-guard` | 只装单个 Skill |
| 已拆分工作的 Agent 执行适配 | `agent-orchestration` | 只装单个 Skill |
| 持续科研项目 | Akira Research | 安装完整 Research suite |
| 持续软件工程项目 | Matt Engineering | 安装完整 Matt fork |
| Knowledge 产品 | 暂不可用 | 不安装 |
| first-party 没有的专业能力 | External Sources | 读取 `EXTERNAL-SOURCES.md`，再按最小候选请求用户授权 |

## 安装边界

- 新能力安装前必须说明来源、用途、安装对象和范围，并取得用户明确同意。
- 所有 Akira 管理的 `npx skills add` 使用 symlink mode；命令不得带 `--copy`，安装后必须核验目标 Skill 为软链接。
- 产品仓默认项目级安装，不使用 `-g`；ForgeRelay 的两个常驻基线由 Lattice 根安装器单独维护。
- 不因一次 Word、PPT、浏览器或 Guard 任务安装 Research / Matt。
- 不因科研项目安装 Matt，也不因软件工程项目安装 Research；真实跨域任务除外。
- 已经可用的同名能力直接复用，不重复安装。
- `planned`、`remote-pending`、`unavailable` 等非 available 状态不得生成看似可执行的安装方案。
