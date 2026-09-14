# akira

`akira` 是 Akira 通用 Skill Router。它解决的不是“如何做科研/开发/写文档”，而是“当前项目还缺哪一组能力，应该从哪个受管仓库安装什么”。

## 主要路由

- 软件工程：安装/使用 Akira 自主维护的 `Akira-TL/matt-skills`；Primary Router 为 `ask-akira`，普通 `standard` 工程流再按需加载 `ask-matt`，Parallel 系列继续负责正式多 Agent coordination。
- 科学研究：安装/使用已发布的独立 `Akira-TL/akira-research-skills`，按项目级范围安装完整 Research suite。
- 浏览器、Word、科研/学术 PPT、Guard、通用 Agent 执行适配：直接使用本仓库中的对应通用 Skill，不需要单独产品仓。
- Knowledge：当前仍为 planned，正式实现后再加入可安装目录。
- 外部能力：当 first-party 能力不足时，Router 只从已登记外部来源动态读取当前 Skill 清单，向用户呈现与任务相关的最小候选；不把外部整仓加入 Lattice，也不因来源可信而跳过安装确认。

Router 默认先复用当前会话已经真实可用的能力；当前会话缺少时再检查机器级 `~/.agents/skills/` 注册表。机器级已经安装的 Skill 不重复安装，并优先通过当前执行器正常的 Skill 加载机制引用。机器级已安装不自动产生项目级投影：`<project>/.agents/skills/` 可以作为开放 Agent Skills 生态中的显式项目级 Skill view；只有项目或执行器确实需要该 view 时，Agent 才可显式建立 `<project>/.agents/skills/<name> -> ~/.agents/skills/<name>` 软链接。该链接不是重新安装，也不能仅凭“当前会话没看到 Skill”自动创建。只有机器级也不存在时才推荐从远端新增 Skill，安装前仍需说明来源、用途和范围并取得用户明确同意。

`routing/akira/references/CATALOG.md` 是 first-party 能力注册表：统一维护我们自有 Skill / 产品族的准确名称、用途、GitHub source、发布状态、安装粒度与推荐命令。真正执行安装、更新、卸载或诊断时再读取 `INSTALLATION.md`；`akira/SKILL.md` 不复制这些详细表。first-party 不足时才继续读取 `EXTERNAL-SOURCES.md`。

Akira 管理的 Skill 只从 Catalog 登记的远端 GitHub source 拉取到 `~/.agents/sources/`，再以软链接注册到机器级 `~/.agents/skills/`。安装逻辑由 `akira` Skill 自带的 `scripts/skills.py` 实现；Lattice 根安装器只允许从云端临时 checkout 调用它 bootstrap `akira`、`browser-access` 与 `akira-guard`，Router 已可用后的其他安装都由 Router 在确认能力缺口并获得用户授权后主动调用。具体执行器或项目自己的 Skill 目录只作为显式 view：可以按项目约定引用 `~/.agents/skills/`，但不会由 Akira 安装器或执行器仅因机器级注册项存在而自动创建、更新或删除。

Word、PPT、Matt、Research 与外部来源都只在真实任务需要时发现和安装；机器级已经安装的 Skill 直接复用，不因为“未来可能用到”继续扩张注册表。同一 GitHub repository 下的已注册 Skill 共用一个 source checkout；checkout 被安装或更新动作推进时，安装器同步刷新该 source 下全部已注册 Skill 的 manifest revision，保持 provenance 与实际文件一致。
