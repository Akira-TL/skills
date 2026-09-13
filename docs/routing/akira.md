# akira

`akira` 是 Akira 通用 Skill Router。它解决的不是“如何做科研/开发/写文档”，而是“当前项目还缺哪一组能力，应该从哪个受管仓库安装什么”。

## 主要路由

- 软件工程：安装/使用 `Akira-TL/matt-skills`；`ask-akira` 与 Parallel 系列属于该 Matt fork 的工程扩展。
- 科学研究：安装/使用独立的 `Akira-TL/akira-research-skills`。
- 浏览器、Word、科研/学术 PPT、Guard、通用 Agent 执行适配：直接使用本仓库中的对应通用 Skill，不需要单独产品仓。
- Knowledge：当前仍为 planned，正式实现后再加入可安装目录。
- 外部能力：当 first-party 能力不足时，Router 只从已登记外部来源动态读取当前 Skill 清单，向用户呈现与任务相关的最小候选；不把外部整仓加入 Lattice，也不因来源可信而跳过安装确认。

Router 默认先复用当前项目已经安装的能力。只有真实任务出现能力缺口时才推荐新增 Skill；专业产品默认项目级安装，并在安装前说明来源、用途和范围，取得用户明确同意。

Akira Lattice 的全局默认只提供 Router 与极少数跨域基线能力。Word、PPT、Matt、Research 等不因为“未来可能用到”自动全局安装。OpenAI Plugins 等外部来源也只在真实任务需要时动态发现并项目级安装具体 Skill。
