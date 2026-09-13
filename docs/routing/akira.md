# akira

`akira` 是 Akira 通用 Skill Router。它解决的不是“如何做科研/开发/写文档”，而是“当前项目还缺哪一组能力，应该从哪个受管仓库安装什么”。

## 主要路由

- 软件工程：安装/使用 `Akira-TL/matt-skills`；`ask-akira` 与 Parallel 系列属于该 Matt fork 的工程扩展。
- 科学研究：安装/使用已发布的独立 `Akira-TL/akira-research-skills`，按项目级范围安装完整 Research suite。
- 浏览器、Word、科研/学术 PPT、Guard、通用 Agent 执行适配：直接使用本仓库中的对应通用 Skill，不需要单独产品仓。
- Knowledge：当前仍为 planned，正式实现后再加入可安装目录。
- 外部能力：当 first-party 能力不足时，Router 只从已登记外部来源动态读取当前 Skill 清单，向用户呈现与任务相关的最小候选；不把外部整仓加入 Lattice，也不因来源可信而跳过安装确认。

Router 默认先复用当前会话已经真实可用的能力；当前会话缺少时再检查机器级 `~/.agents/skills/` 注册表。机器级已经安装的 Skill 不重复安装，由当前执行器按自己的 Skill 机制发现、引用或链接；只有机器级也不存在时才推荐从远端新增 Skill，安装前仍需说明来源、用途和范围并取得用户明确同意。

`routing/akira/references/CATALOG.md` 是 first-party 能力注册表：统一维护我们自有 Skill / 产品族的准确名称、用途、GitHub source、发布状态、安装粒度与推荐命令。真正执行安装、更新、卸载或诊断时再读取 `INSTALLATION.md`；`akira/SKILL.md` 不复制这些详细表。first-party 不足时才继续读取 `EXTERNAL-SOURCES.md`。

Akira 管理的 Skill 只从 Catalog 登记的远端 GitHub source 拉取到 `~/.agents/sources/`，再以软链接注册到机器级 `~/.agents/skills/`。安装逻辑由 Lattice 自带的 `scripts/skills.py` 实现，不依赖第三方 Skill package manager，也不管理 ForgeRelay、Claude Code、Codex 或其他执行器自己的 Skill 目录。

Word、PPT、Matt、Research 与外部来源都只在真实任务需要时发现和安装；机器级已经安装的 Skill 直接复用，不因为“未来可能用到”继续扩张注册表。
