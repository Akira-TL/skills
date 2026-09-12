# 第三方科研 Skill 第一轮审计

本文件记录 Akira Research 对外部科研 Skill 的职责判断与吸收边界。它不是第三方源码镜像；第三方正文不复制进 Akira。

审计日期：2026-09-12。

## 1. `leo-lilinxiao/codex-autoresearch`

审计 revision：`d65f7c6c6718e9b795e97b907d09a4e361b32a1f`

仓库 license：MIT。

### 吸收

吸收进 `analysis` / Analysis Attempt 的思想：

- 适用于存在稳定机械指标的迭代问题；
- 先固定 baseline、metric、方向、target 和 guard；
- 一次 Attempt 只做一个可解释的改动；
- 测量失败、guard 失败和未改善必须显式保留原因；
- benchmark 本身不稳定时先修测量方法，不把噪声解释成进步；
- run state / event history 应 fail closed，不靠会话记忆猜测。

### 不吸收

- 不让第三方 controller 接管 Akira 科研 branch 的 commit / revert 生命周期；
- 不把“指标变好”自动等同于 scientific validity；
- 不对已进入科研 provenance 的 commit 做 destructive history rewrite；
- 不把所有科研探索强行压成单一数值优化问题。

运行时定位：`reference-only / isolated-only`，不是 Akira Research 的默认执行依赖。

## 2. `Yuan1z0825/nature-skills`

审计 revision：`c4e4c99fbeaf0168cda090f8739e1508017a610e`

仓库 license：Apache-2.0。

### 吸收

吸收进 `communication` 的思想：

- 论文应能被还原成明确的全文论证链；缺失环节要显式暴露，不能靠 prose 绕过；
- Results 使用 evidence ladder，而不是 Figure 的平铺罗列；
- paragraph flow 以“一个段落一个主信息、句间关系明确”为基础；
- 使用 reverse outlining 检查 section thesis、段落主题句和证据之间的映射；
- 投稿前用 reviewer 视角检查 technical soundness、贡献、评价完整性、可读性等风险；
- reviewer comment 必须映射到实际 text / analysis / experiment / figure / citation / claim-softening 等动作，回复文字本身不是完成证据；
- 无法完成或超出研究设计的问题要显式说明 partial / out-of-scope，而不是假装已经解决。

### 不吸收

- Nature / Nature Communications 特有的编辑标准不升级为所有期刊通用门禁；
- “跨学科读者兴趣”“outstanding importance”等只在目标期刊确实要求时使用；
- 不安装第二套 writing / reviewer Router 与 Akira Communication 并行竞争。

运行时定位：`absorbed-reference`；当前不作为平级科研 Router 安装。

## 3. `Imbad0202/academic-research-skills`

审计 revision：`f1a57bbcabf5cf3da9654ac4d54d056dc6b4b7ea`

仓库 license：Creative Commons Attribution-NonCommercial 4.0 International（CC BY-NC 4.0）。

因此 Akira **只吸收方法思想并独立重写规则，不复制其正文、schema、模板或 pipeline 实现。**

### 吸收

吸收进 `communication` 的思想：

- draft 完成后、正式 reviewer-style review 前先做一次 integrity audit；
- revision 完成后、finalize 前再做最终 integrity audit；
- headline / numerical / causal / methods-critical / disputed Claim 属于优先核验对象；
- citation identity 正确不等于 citation 真正支持正文 Claim；需要 claim-to-source 核验；
- 对无法访问或无法核验的 source 保持 `unresolved / unverifiable`，不能用缺失信息制造 PASS；
- 最终稿修订后重新检查 claim strength、数值、limitation、scope 和 citation 是否发生未授权漂移；
- re-review 先固定原 reviewer concern 的验收标准，再独立检查 revised manuscript 的实际证据，最后才读取作者 response letter，避免被说服性文字锚定；
- “作者说已经修改”与“可核验 artifact 证明已经修改”必须分开。

### 不吸收

- 不引入其完整 research→write→review→revise→finalize state machine；
- 不引入第二套 Research Router、数据库 schema、Agent roster 或专属 pipeline artifact system；
- 不机械照搬固定采样比例、评分或 journal decision 算法；Akira 根据传播风险和当前材料决定审计强度。

运行时定位：`absorbed-reference / blocked-runtime-router`。

## 4. `K-Dense-AI/scientific-agent-skills`

本轮仅核验为按需外部 Skill 来源，不吸收整仓工具正文。

审计时上游 HEAD：`c1ed16d97dd61ff50a3bd46dd353e4a55fd77f34`。

仓库 README 标示整体 MIT，但同时存在 vendored / community Skill；**安装前仍必须检查具体 Skill 自己的 license、脚本和外部依赖。**

定位：`project-local-on-demand`。

- 不加入 Akira Lattice submodule；
- 不加入全局 `install.sh`；
- 不批量安装；
- 当前任务需要某一专业能力时，先审计那个具体 Skill，再向用户请求项目级安装许可；
- 安装命令与权限边界见 [`POLICY.md`](POLICY.md)。
