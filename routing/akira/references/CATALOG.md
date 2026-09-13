# Akira 能力目录

本文件是 `akira` Router 的 **first-party 能力注册表**，也是“当前有哪些能力、从哪里安装、应安装单个 Skill 还是完整产品族”的唯一 source of truth。

`akira/SKILL.md` 只负责判断何时查能力；具体 Skill 名称、GitHub source、发布状态、安装粒度与推荐安装命令只在这里维护。Router 不从旧会话记忆、本机残留目录或 GitHub 搜索结果猜测 first-party 能力。

## 使用规则

出现以下任一情况时读取本文件：

- 当前任务需要尚未可用的能力；
- 用户询问“有什么 Skill / 应该安装什么”；
- 需要决定安装单个通用 Skill，还是完整 Research / Matt 产品族；
- 需要生成准确安装命令；
- 需要确认某个产品当前是 `available`、`planned` 还是不可安装。

如果当前能力已经满足任务，不为“以后可能用到”安装更多产品。安装机制的详细语义见 [`INSTALLATION.md`](INSTALLATION.md)；外部第三方能力见 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md)。

## Akira 通用 Skills

GitHub source：`https://github.com/Akira-TL/skills.git`

| Skill | 能力 | 默认状态 | 何时安装 |
| --- | --- | --- | --- |
| `akira` | 能力 Router；决定当前项目还缺什么 | 基础能力 | 机器级缺失时安装 |
| `browser-access` | 动态/认证网页访问、浏览器控制、登录态复用 | 基础能力 | 机器级缺失时安装 |
| `general-word-document-generation` | 正式 Word / DOCX 文档生成与编辑 | 按需 | 当前任务明确需要 DOCX |
| `scientific-presentation-authoring` | 科研/学术 PPT 内容组织与交付 | 按需 | 当前任务明确需要科研或学术演示文稿 |
| `akira-guard` | Akira Guard 的使用语义、排障与边界 | 按需 | 需要理解/诊断 Guard，而不是仅执行已有 Guard 命令 |
| `agent-orchestration` | 把已定义工作单元映射到当前 harness 的 Agent 执行原语 | 按需 | 任务已经拆好，且当前 harness 提供可用多 Agent / 并行原语 |

单个通用 Skill 的机器级安装：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill <skill-name>
```

这些通用 Skill 不拥有 Research 状态机，也不复制 Matt 工程方法论。

## Akira Research

- GitHub source：`https://github.com/Akira-TL/akira-research-skills.git`
- Status：available
- Primary Router：`akira-research`
- 安装粒度：持续科研项目需要完整 Research suite 时，将整套能力安装到机器级注册表；机器级已有时不重复安装。

安装完整 Research suite：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/akira-research-skills.git \
  --all \
  --root skills/research
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

安装后由 `akira-research` 接管后续路由，`akira` 不直接执行科研工作。

## Matt Engineering

- GitHub source：`https://github.com/Akira-TL/matt-skills.git`
- Status：available
- Primary Router：`ask-matt`
- 安装粒度：持续软件工程需要时，将 promoted Matt suite 与 Akira fork 的三个工程扩展安装到机器级注册表。

安装：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/matt-skills.git \
  --all \
  --root skills/engineering \
  --root skills/productivity \
  --skill ask-akira \
  --skill parallel-coordinator \
  --skill parallel-execution
```

这里 `--root` 只安装 Matt promoted 的 `engineering` / `productivity` 两个产品目录；三个显式 `--skill` 再加入 Akira fork extensions，避免仓库其他 `misc` / 实验性 Skill 因 `--all` 被自动带入。

Matt fork 提供需求澄清、Spec/Ticket、实现、TDD、代码审查、缺陷诊断、重构、工程写作等工程能力。Akira 自有增量：

| Skill | 能力 |
| --- | --- |
| `ask-akira` | 在 Matt 工程方法上增加 Akira 项目协作与路由 |
| `parallel-coordinator` | 发布和协调 Parallel Task / Gate 工作 |
| `parallel-execution` | Worker 领取、执行、提交和阶段汇报协议 |

这些增量不是第二套工程体系；安装 Matt 后，以 `ask-matt` / `ask-akira` 继续路由。

## Akira Knowledge

- Planned source：`https://github.com/Akira-TL/akira-knowledge-skills.git`
- Status：planned
- 用途：知识采集、概念关系、长期笔记、知识总结与复习工作流。

当前没有可安装实现。不得生成伪造命令，也不得因为规划存在就把它描述为 available。

## 快速选择表

| 当前需求 | 选择 | 安装策略 |
| --- | --- | --- |
| 动态网页 / 登录态 / 浏览器 | `browser-access` | 机器级缺失时装单个 Skill |
| Word / DOCX | `general-word-document-generation` | 机器级缺失时装单个 Skill |
| 科研/学术 PPT | `scientific-presentation-authoring` | 机器级缺失时装单个 Skill |
| Guard 语义/排障 | `akira-guard` | 机器级缺失时装单个 Skill |
| 已拆分工作的 Agent 执行适配 | `agent-orchestration` | 机器级缺失时装单个 Skill |
| 持续科研项目 | Akira Research | 机器级缺失时安装完整 Research suite |
| 持续软件工程项目 | Matt Engineering | 机器级缺失时安装 promoted Matt + Akira extensions |
| Knowledge 产品 | 暂不可用 | 不安装 |
| first-party 没有的专业能力 | External Sources | 读取 `EXTERNAL-SOURCES.md`，再按最小候选请求用户授权 |

## 安装边界

- 新能力安装前必须说明来源、用途、安装对象和范围，并取得用户明确同意。
- 安装器只接受登记过或用户明确批准的远端 GitHub source；运行时 Skill 不从 Lattice 本地 submodule checkout 安装。
- Skill 实体只存在于 `~/.agents/sources/<owner>/<repo>/` 的 Git checkout；`~/.agents/skills/` 只保存机器级软链接注册项。
- `~/.agents/skills/` 是机器级已安装 Skill 注册表。当前执行器缺少能力时先检查这里；已注册则由执行器按自己的 Skill 机制复用，未注册才从远端 GitHub 安装。
- Akira 不规定项目级 Skill 目录，也不规定 ForgeRelay、Claude Code、Codex 或其他执行器如何暴露机器级 Skill。
- 更新只更新 Git source checkout；软链接不需要重新复制或重装。
- 不因一次 Word、PPT、浏览器或 Guard 任务安装 Research / Matt。
- 不因科研项目安装 Matt，也不因软件工程项目安装 Research；真实跨域任务除外。
- 已经可用的同名能力直接复用，不重复安装。
- `planned`、`remote-pending`、`unavailable` 等非 available 状态不得生成看似可执行的安装方案。
