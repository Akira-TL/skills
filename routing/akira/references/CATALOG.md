# Akira Skill 能力目录

本文件是 `akira` Router 判断“当前项目还需要安装什么”的唯一产品目录。Router 不从 GitHub 搜索结果、旧会话记忆或本机偶然存在的目录推断产品状态。

## 通用 Akira Skills

- Source：`Akira-TL/skills`
- Ownership：本仓库
- Status：available
- 用途：跨领域、可单独复用的通用能力，以及产品安装 Router。
- 默认全局基线：`akira`、`browser-access`。
- 按需能力：`akira-guard`、`agent-orchestration`、`general-word-document-generation`、`scientific-presentation-authoring`。
- 安装策略：已经存在的全局基线直接复用；缺少某个按需能力时，只安装该 Skill，不因一次文档、PPT 或 Agent 编排需求安装其他产品仓。

通用能力不拥有科研状态机或 Matt 工程方法论。`agent-orchestration` 只适配当前 harness 已有执行原语，不接管 Parallel Task / Gate 协议。

## Matt Engineering

- Source：`Akira-TL/matt-skills`
- Local source in Lattice：`skills/matt`
- Status：available
- Primary Router：`ask-matt`
- Akira fork extensions：`ask-akira`、`parallel-coordinator`、`parallel-execution`，均位于 Matt fork 的 `skills/in-progress/`。
- 用途：软件工程的需求澄清、Spec/Ticket、实现、TDD、代码审查、缺陷诊断、特殊速度模式与正式多 Agent 工程协作。
- Recommended install：软件工程项目默认安装 Matt fork 的完整 Skill suite；不要再安装一个独立 Akira Engineering 产品仓。

`ask-akira` 与 Parallel 系列是 Matt 工作流的增量，不是第二套工程方法论，因此与 Matt fork 同仓维护。

## Akira Research

- Source：`Akira-TL/akira-research-skills`
- Local canonical checkout：`/home/Akira/Projects/akira-research-skills`
- Status：available
- Primary Router：`akira-research`
- 用途：Research Question、Research Tree、Literature、Hypothesis、Design、Study、Data、Analysis、Interpretation、Communication 与 research.sqlite provenance。
- Recommended install：`npx skills add Akira-TL/akira-research-skills --skill '*' --agent '*' -y`。

Research 内部共享 schema、migration、Research Tree 与对象契约，保持为独立高内聚产品仓。科研项目需要完整 Research 工作流时，按项目级范围安装整个 suite，不作为全局默认能力。

## 外部能力源

外部 Skill 不作为本目录中的产品仓，也不由 Lattice 预先固定源码。当前登记来源、动态发现方式与安装边界见 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md)。当 first-party 能力不足时，Router 可以从已登记来源查当前 Skill 清单，但只能推荐与任务直接相关的最小候选，并在安装前再次取得用户同意。

## Akira Knowledge

- Source：未来 `Akira-TL/akira-knowledge-skills`
- Status：planned
- 用途：知识采集、概念关系、长期笔记、知识总结与复习工作流。

当前没有可安装实现。遇到知识类项目时可以说明规划方向，但不得伪造安装命令、目录或已存在的 Skill 名称。

## 组合原则

先选择项目的主要能力域，再按真实任务增加最小补充能力：

- 科研项目：Research；需要认证网页时复用/补装 `browser-access`，需要正式 DOCX 或 PPT 时再补对应通用 Skill。
- 软件工程项目：Matt Engineering；只有当前 harness 已有多 Agent 执行原语且上游任务适合并行时才使用相关 Akira 扩展。
- 通用浏览器、Word、PPT 或 Guard 任务：直接使用本仓库对应 Skill，不引入 Research 或 Matt。
- 跨域项目：每增加一个产品仓或按需 Skill 都必须有当前任务触发，不以“以后可能用到”为理由预装。
