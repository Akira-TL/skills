# akira

`akira` 是 Akira 通用 Skill Router。它解决的不是“如何做科研/开发/写文档”，而是“当前项目还缺哪一组能力，应该从哪个受管仓库安装什么”。

## 主要路由

- 软件工程：安装/使用 `Akira-TL/matt-skills`；`ask-akira` 与 Parallel 系列属于该 Matt fork 的工程扩展。
- 科学研究：安装/使用已发布的独立 `Akira-TL/akira-research-skills`；采用 Akira 共享注册表时安装完整 Research suite，独立 Skill store 则遵守执行器自己的安装机制。
- 浏览器、Word、科研/学术 PPT、Guard、通用 Agent 执行适配：直接使用本仓库中的对应通用 Skill，不需要单独产品仓。
- Knowledge：当前仍为 planned，正式实现后再加入可安装目录。
- 外部能力：当 first-party 能力不足时，Router 只从已登记外部来源动态读取当前 Skill 清单，向用户呈现与任务相关的最小候选；不把外部整仓加入 Lattice，也不因来源可信而跳过安装确认。

Router 默认先复用当前会话已经真实可用的能力。当前会话缺少时，只有明确采用 Akira 共享注册表的执行器才继续检查机器级 `~/.agents/skills/`；使用独立 Skill store 的执行器只检查自己的来源，不得自动建立到 `~/.agents/skills/` 的适配链接。仍缺少能力时，再由 Catalog 确定远端 source 与最小 Skill 集合，安装前仍需说明来源、用途和范围并取得用户明确同意。

`routing/akira/references/CATALOG.md` 是 first-party 能力注册表：统一维护我们自有 Skill / 产品族的准确名称、用途、GitHub source、发布状态、安装粒度与推荐命令。真正执行安装、更新、卸载或诊断时再读取 `INSTALLATION.md`；`akira/SKILL.md` 不复制这些详细表。first-party 不足时才继续读取 `EXTERNAL-SOURCES.md`。

对采用 Akira 共享注册表的执行器，受管 Skill 只从 Catalog 登记的远端 GitHub source 拉取到 `~/.agents/sources/`，再以软链接注册到机器级 `~/.agents/skills/`；安装逻辑由 Lattice 自带的 `scripts/skills.py` 实现。独立 Skill store 不属于这套安装契约，其 source、常驻集合与按需加载方式由对应执行器自己管理。

Word、PPT、Matt、Research 与外部来源都只在真实任务需要时发现和安装；采用共享注册表时复用既有机器级 Skill，采用独立 Skill store 时只按执行器自己的实际需求扩张，不因为“未来可能用到”预装。
