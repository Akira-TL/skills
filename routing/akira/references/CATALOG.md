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
| `akira` | 能力 Router；决定当前项目还缺什么 | 基础能力 | Lattice 根安装器从云端 bootstrap，并调用本 Skill 自带安装器完成注册 |
| `browser-access` | 动态/认证网页访问、浏览器控制、登录态复用 | 基础能力 | 机器级缺失时安装 |
| `general-word-document-generation` | 正式 Word / DOCX 文档生成与编辑 | 按需 | 当前任务明确需要 DOCX |
| `scientific-presentation-authoring` | 科研/学术 PPT 内容组织与交付 | 按需 | 当前任务明确需要科研或学术演示文稿；中文文案终检阶段按需补 `humanizer-zh` |
| `akira-guard` | 跨项目 Git Guard、暂存语法检查、架构/Skill 结构检查及其使用语义 | 基础能力 | Lattice 根安装器从云端 bootstrap；正式 Git 提交默认使用其脚本 |
| `agent-orchestration` | 把已定义工作单元映射到当前 harness 的 Agent 执行原语 | 按需 | 任务已经拆好，且当前 harness 提供可用多 Agent / 并行原语 |

单个通用 Skill 的机器级安装：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill <skill-name>
```

这些通用 Skill 不拥有 Research 状态机，也不复制 Matt 工程方法论。

`scientific-presentation-authoring` 的中文文案终检显式依赖外部 `humanizer-zh`，但该依赖不属于 first-party Catalog，也不进入默认 bootstrap。需要时按 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md) 登记的来源检查当前会话与机器级注册表，机器级缺失时再请求用户授权并安装。

## Akira Research

- GitHub source：`https://github.com/Akira-TL/akira-research-skills.git`
- Status：available
- Primary Router：`akira-research`
- 安装粒度：持续科研项目需要完整 Research suite 时，将整套能力安装到机器级注册表；机器级已有时不重复安装。

安装完整 Research suite：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
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
- Primary Router：`ask-akira`
- 安装粒度：持续软件工程需要时，将稳定 Matt suite（已包含 `ask-akira`）与两个 Parallel 扩展安装到机器级注册表。

安装：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/matt-skills.git \
  --all \
  --root skills/engineering \
  --root skills/productivity \
  --skill parallel-coordinator \
  --skill parallel-execution
```

这里 `--root` 安装 Matt 稳定的 `engineering` / `productivity` 两个产品目录，其中已包含 `ask-akira`；两个显式 `--skill` 再加入仍处于实验阶段的 Parallel 扩展，避免仓库其他实验性 Skill 因 `--all` 被自动带入。

Akira 自主维护的 Matt Engineering 提供需求澄清、Spec/Ticket、实现、TDD、代码审查、缺陷诊断、重构、工程写作等工程能力，并包含以下 Akira 工程扩展：

| Skill | 能力 |
| --- | --- |
| `ask-akira` | Engineering Primary Router；默认进入 standard，并拥有特殊 Execution Policy 与协调边界 |
| `parallel-coordinator` | 发布和协调 Parallel Task / Gate 工作 |
| `parallel-execution` | Worker 领取、执行、提交和阶段汇报协议 |

这些能力不是第二套工程体系；安装 Matt 后由 `ask-akira` 接管软件工程入口，`standard` 分支再按需加载 `ask-matt` 解析 Matt standard flow。

## Akira Knowledge

- GitHub source：`https://github.com/Akira-TL/akira-knowledge-skills.git`
- Status：unavailable；产品仓已初始化，但当前没有可安装 Skill
- Planned Primary Router：`akira-knowledge`
- 用途：长期知识管理；具体对象模型与内部 Skill 边界尚未定稿。

当前只存在产品仓与已确认的产品边界，不存在可安装实现。不得生成安装命令，也不得把仓库已创建等同于产品已发布。

## 快速选择表

| 当前需求 | 选择 | 安装策略 |
| --- | --- | --- |
| 动态网页 / 登录态 / 浏览器 | `browser-access` | 机器级缺失时装单个 Skill |
| Word / DOCX | `general-word-document-generation` | 机器级缺失时装单个 Skill |
| 科研/学术 PPT | `scientific-presentation-authoring` | 主 Skill 机器级缺失时安装；中文文案终检需要 `humanizer-zh` 时再按 External Sources 按需安装 |
| Git 提交、Guard 检查与 Guard 语义/排障 | `akira-guard` | 基础 bootstrap；缺失时修复安装 |
| 已拆分工作的 Agent 执行适配 | `agent-orchestration` | 机器级缺失时装单个 Skill |
| 持续科研项目 | Akira Research | 机器级缺失时安装完整 Research suite |
| 持续软件工程项目 | Matt Engineering | 机器级缺失时安装稳定 Matt suite + Parallel 扩展 |
| Knowledge 产品 | 暂不可用 | 不安装 |
| first-party 没有的专业能力 | External Sources | 读取 `EXTERNAL-SOURCES.md`，再按最小候选请求用户授权 |

## 安装边界

- 新能力安装前必须说明来源、用途、安装对象和范围，并取得用户明确同意。
- 安装器只接受登记过或用户明确批准的远端 GitHub source；运行时 Skill 不从 Lattice 本地 submodule checkout 安装。
- Skill 实体只存在于 `~/.agents/sources/<owner>/<repo>/` 的 Git checkout；`~/.agents/skills/` 只保存机器级软链接注册项。
- `~/.agents/skills/` 是机器级已安装 Skill 注册表。当前会话缺少能力时先检查这里；已注册则不重复安装，未注册才从远端 GitHub 安装。
- 机器级已注册 Skill 优先由当前执行器通过正常 Skill 加载机制引用，不自动投影到执行器或项目目录。若项目或执行器明确需要自己的 Skill view，可显式建立指向 `~/.agents/skills/<name>` 的软链接；`<project>/.agents/skills/` 是允许的项目级 Agent Skills view。此类链接不是新的安装，也不得仅因当前会话未暴露 Skill 而自动创建；Akira 不规定这些 view 的路径，也不替执行器管理这些链接。
- 更新只更新 Git source checkout；软链接不需要重新复制或重装。
- 不因一次 Word、PPT、浏览器或 Guard 任务安装 Research / Matt。
- 不因科研项目安装 Matt，也不因软件工程项目安装 Research；真实跨域任务除外。
- 已经可用的同名能力直接复用，不重复安装。
- `planned`、`remote-pending`、`unavailable` 等非 available 状态不得生成看似可执行的安装方案。
