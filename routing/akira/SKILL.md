---
name: akira
description: 判断当前项目需要哪些 Akira / Matt Skill 能力并保持最小安装；当开始新项目、项目缺少一类能力、用户询问应安装什么 Skill，或任务跨到尚未安装的科研、工程、浏览器、文档、PPT 等能力时使用。
---

# Akira Skill Router

`akira` 是通用能力 Router，不替代 Research、Matt 或其他专业 Skill。它负责根据当前项目持续工作的主要类型和当前真实任务，决定是否需要补装新的 Skill，并把安装范围控制在最小充分集合。

## 1. 先看现有能力

先检查当前项目已经存在的 `.agents/skills/`、`skills-lock.json` 和当前会话真实可用能力，再判断缺口。不要因为目录中有某类文件就自动定义项目类型，也不要重复安装已经可用的同名 Skill。

读取 [`references/CATALOG.md`](references/CATALOG.md) 获取受管仓库、发布状态、默认基线与安装边界。目录是本 Router 的 source of truth。

完成标准：能够说明当前任务缺的是“通用单一能力”还是“完整产品域”。

## 2. 优先补单一通用能力

本仓库同时承载通用 Productivity / Guard / harness 适配 Skill。任务只缺以下能力时，不安装完整专业产品仓：

- 动态网页、登录态或人工认证边界 → `browser-access`；
- 正式 Word 文档 → `general-word-document-generation`；
- 科研 / 学术汇报 → `scientific-presentation-authoring`；
- Guard 语义与故障排查 → `akira-guard`；
- 已定义工作单元到当前 harness 执行原语的适配 → `agent-orchestration`。

默认全局基线由 Akira Lattice 管理；缺少其他通用能力时，只补当前 Skill。

## 3. 完整产品域才安装产品仓

只有当前项目的主要持续工作需要一整套内部协作能力时，才推荐产品仓：

- 软件工程 → Matt fork；以 `ask-matt` 为 Router，`ask-akira` 与 Parallel 系列作为同仓的 Akira 工程扩展；
- 科学研究 → Akira Research；以 `akira-research` 为 Router；
- 知识积累 / 长期总结 → 只有 Catalog 标记为 available 后才推荐 Knowledge。

Research、Matt 等默认**项目级安装**，不使用 `-g`。跨域需求出现时再增加第二个产品，不因“可能以后用到”预装。

## 4. 安装必须先获得用户同意

准备安装尚未存在的 Skill / 产品仓时，先向用户说明：

```text
来源仓库
当前任务为什么需要
计划安装的 Skill 或完整产品族
安装范围：当前项目
当前发布状态
```

用户明确同意后才能执行。通用单一能力使用：

```bash
npx skills add Akira-TL/skills --skill <skill-name> --agent '*' -y
```

Matt 或其他完整产品按 Catalog 的 `recommended install` 执行。若目标处于 `remote-pending`、`planned` 或其他不可直接取得状态，保持 blocker / 本地维护路径边界，不把未来仓库伪装成已发布来源。

## 5. 安装后交给真实 Owner

安装成功后只核验所需 Skill 确实出现，然后把工作交给对应 Owner：

- Matt 工程 → `ask-matt` 或它路由出的工程 Skill；
- Research → `akira-research`；
- 通用能力 → 直接调用对应 Productivity / Guard / orchestration Skill；
- Knowledge → 未来 Knowledge Router。

后续出现新的能力缺口时重新走本 Router；已经安装某个产品不授权自动扩张其他产品。
