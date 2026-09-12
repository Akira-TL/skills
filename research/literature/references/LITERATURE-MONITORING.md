# 长期文献监测（Living Literature Monitoring）

本文件用于一个科研问题已经形成、项目需要在数周到数年内持续发现新证据的场景。它不是新的系统综述方法，也不是“每天给用户推论文”的资讯订阅；目标是让新的 scholarly work 持续回到同一 Research Tree、Search Run、Candidate、Paper 与 Evidence Gate。

## 1. 监测围绕科学问题，不围绕关键词热度

只有存在稳定 Objective、Research Question、Active Uncertainty、Open Thread、方法路线或明确长期主题时才建立 monitor。每个 monitor 至少说明：

- `purpose`：为什么持续追踪；
- `scientific_scope`：对应哪个 Question / uncertainty / method / population / claim；
- `sources`：实际使用哪些数据库、预印本、注册平台、数据/代码仓库或引文网络；
- `queries / seeds`：当前检索式、关键作者/工作或 citation seed；
- `cadence`：由研究变化速度决定的日 / 周 / 月等频率；
- `notification_threshold`：什么变化值得打扰用户；
- `last_successful_run`：上一次真实完成的监测时间。

不要因为工具支持定时任务就给所有项目建立监测。

## 2. 每次监测仍然是正式 Search Run

一次 monitor execution 不维护第二套“雷达数据库”。实际搜索继续使用现有 `research-db record-search`，`discovery_method` 优先使用真实的 `update_search`；若本次实际是 citation chasing、method search 等，则记录真实方法，不为了监测功能伪造枚举。

循环：

```text
monitor scope
→ 执行本期 query / citation update
→ 与既有 Candidate / Paper 稳定身份去重
→ 只处理真正新增或版本实质变化的 scholarly work
→ relevance / reading priority 判断
→ 必要全文获取与阅读
→ 判断是否改变 Evidence Map / Active Uncertainty / Open Threads
→ 保存 Search Run 与 next decision
```

重复命中不是新 evidence；同一 DOI / PMID / scholarly work 被多个来源重复发现时保留多条 discovery provenance，但只维护一个 Candidate / Paper identity。

## 3. 什么值得通知用户

默认静默记录普通新增文献。只有至少出现以下一种变化时才主动通知：

- 新 evidence 实质支持、削弱、限定或反驳当前主要 Claim / Hypothesis；
- 新论文引入 previously untested competing explanation；
- 新方法可能明显改变当前 Design / Analysis 路线；
- 新 population / condition / failure case 改变已知 boundary；
- 高价值 replication / failed replication；
- 影响当前投稿、系统综述更新或研究设计的 guideline / standard / registration 变化；
- 用户明确要求的某篇论文、作者、数据集或方法出现新版本。

“本周新增 17 篇相关论文”本身不是通知理由。没有改变科研判断的新增论文可以进入 reading queue，而不是制造日报噪声。

## 4. 推荐阅读与阅读队列

Monitor 可以把值得人亲自阅读的论文提升为 `reading_priority=core|high`。这一优先级表示 Agent 推荐阅读顺序，不表示用户已经阅读或同意该论文结论。

若用户使用 Zotero，可按 [`ZOTERO-EXPORT.md`](ZOTERO-EXPORT.md) 把这些推荐项送入固定的 `Akira Recommended Reading` collection；Akira 不继续替用户维护 Zotero 分类结构。

## 5. 与自动化 / scheduler 的边界

若当前 Agent harness 确实提供定时任务或自动化能力，并且用户明确同意 cadence，可以把同一 monitor instruction 交给 scheduler 周期执行。自动化只负责“到点触发本次 Literature update”；真正的 scholarly identity、Search Run、Candidate、Paper、Critical Audit 和 scientific synthesis 仍回写项目 canonical state。

若当前环境没有可靠 scheduler，不伪装成持续后台运行。保存当前 monitor 定义和最后执行点，下一次科研会话继续即可。

不得为了“保持活跃”轮询网页，也不得在平台不支持自动化时反复尝试创建后台任务。

## 6. Systematic Review 的 update search 另受 protocol 约束

普通 Living Monitoring 可以迭代 query；正式系统综述 / 范围综述 / 荟萃分析的 update search 必须继续服从 frozen protocol、目标 reporting guideline 和 `SYSTEMATIC-REVIEW.md`。不能把普通 monitor 的灵活查询替代正式 review 更新方法。

若 SYSTEMATIC update search 新增 included study，受影响的 extraction、appraisal、Analysis、Interpretation 与 Communication 必须按原有规则重新打开。

## 7. 停止或暂停监测

出现以下情况之一可以暂停/关闭：

- 对应 Research Question / branch 已关闭，且新证据不会影响主要结论；
- 项目停止或用户明确不再追踪；
- 查询长期只返回重复/低相关结果，且没有现实信息增益；
- 新 monitor 已完全取代旧 scope。

关闭 monitor 不删除历史 Search Run。若以后重新打开，先从最后一次成功运行之后更新，而不是把旧文献当成新发现。