# Regulated Research Authority Boundary

本文件用于涉及伦理审查、人类受试者、个人/敏感数据、临床研究、动物研究、受监管样品、跨境数据/材料、许可或其他 institution / jurisdiction-specific 要求时，约束 `research-standards` 如何识别**适用的权威来源与适用性状态**。

它不是法律意见、伦理委员会决定、机构批准、豁免证明或研究授权。Akira 可以帮助查找和整理规则，但不能替代有权作出正式决定的机构或人员。

## 1. “找到规则”与“规则适用”是两件事

必须分别回答：

1. 当前权威规则/政策是什么？
2. 它为什么适用于当前项目？

不能因为找到一份 IRB / data-protection / animal-research guideline，就自动断言当前研究受它约束；也不能因为稿件没有写某项批准，就自动断言它不适用或作者违规。

适用性判断所需事实可能包括：

```text
研究实际实施地点 / institution
participant / sample / data origin
研究对象与 intervention / observation 类型
data identifiability / sensitivity
数据访问、处理、传输与存储位置
prospective / retrospective / secondary-use status
clinical / regulated-device / drug status（若适用）
跨境或多中心关系
funder / consortium / institutional overlay
研究实际时间与适用规则的时间版本
```

只收集真正影响当前适用性的问题，不把它变成无穷尽的合规问卷。

## 2. 不从弱线索推断 jurisdiction 或 approval

不得仅从以下信息推断适用 authority、伦理路径或批准状态：

- 用户当前 IP / locale；
- 对话语言；
- 作者姓名或国籍；
- affiliation 名称本身；
- 文件路径、项目目录或稿件语言；
- Methods 中出现某国家/机构名称但未说明研究治理关系；
- 模型记忆中“通常这个领域会……”的经验。

Affiliation、研究地点或数据来源可以成为待核验线索，但正式适用性必须由项目事实与当前权威来源共同支撑。

同样，不得从一段 manuscript wording 反推“已有 IRB approval”“已获 waiver”“已取得 consent”“GDPR 不适用”等行政事实。

## 3. Unknown 不能降格成 Not Applicable

对当前需要判断的 regulated requirement，至少区分：

```text
applicable_and_verified
not_applicable_and_verified
applicability_unresolved
```

`applicability_unresolved` 包括：

- 关键项目事实未知；
- jurisdiction / institution authority 未确认；
- 当前规则版本或 effective period 未核验；
- 多个 authority 的关系尚未由有权人员解释；
- exemption / waiver / secondary-use route 可能存在，但没有正式决定。

缺信息不能写成 `not applicable`。同理，某个 exception / waiver route **存在**，不等于当前研究已经符合、申请或获得该例外。

## 4. 权威来源必须检查当前性与职责

涉及 regulated requirement 时，优先使用：

1. 当前 controlling authority / regulator / official legal or policy source；
2. 当前 institution / IRB / REC / data-protection / animal-care office 的正式 guidance；
3. funder / consortium 的正式 requirement；
4. 正式专业组织 guidance 作为方法或解释补充。

记录时至少保留：

```text
authority / policy name
role
scope / applies_to
official source
version / effective date（若影响判断）
verified_at
applicability basis
applicability state
formal decision maker / responsible office（若适用）
```

网页更新日期、法规发布日期、修订日期与实际生效日期不是同一概念；当时间会改变适用性时要核验真正 relevant 的 effective period，不凭页面日期猜。

官方翻译、机构摘要或第三方解释可以帮助理解，但如果 controlling language / controlling source 与翻译不同，不能把翻译当成更高 authority。

## 5. 多个 authority 并列，不由 Agent 私自消解

多中心、跨境、合作机构、funder overlay 或不同监管轴可能同时产生要求。此时：

- 分别记录各 authority 及其适用依据；
- 不把多个 requirement 合并成一个“平均规则”；
- 不因为一个 authority 更宽松就静默压掉另一个；
- 不机械采用“最严格的一条”来冒充正式法律/机构判断；
- 如果规则冲突或 precedence 不清，状态保持 `applicability_unresolved`，交给有权 institution / committee / legal / data-protection role 解决。

排序只用于展示，不改变 authority 本身。

## 6. 规范职责仍需分层

以下对象不能混为一谈：

- **法律 / regulation / institutional policy**：规定是否需要某种正式 review / authorization / protection；
- **伦理 / review authority decision**：由有权机构对具体项目作出的 approval / exemption / waiver / determination；
- **research design / conduct guidance**：研究如何设计和实施；
- **reporting guideline**：论文需要报告什么；
- **data / metadata / repository requirement**：数据如何保存、描述、共享；
- **funder / journal policy**：资助或投稿层面的附加要求。

例如 reporting guideline 要求“报告伦理审批号”并不证明当前项目必须由该 guideline 来决定是否需要伦理审查；该适用性应回到实际 authority。

## 7. Evidence holder 与责任主体不能混淆

某项证明可能由不同主体持有：研究团队、IRB/REC、institution、data controller、repository、funder 等。Agent 不能把“团队当前手头没有某文件”直接解释成“该 approval / decision 不存在”。

应区分：

```text
requirement / decision
responsible authority
expected evidence
who should hold it
current project evidence available?
```

外部 authority 才能出具的 decision 不应被转化成“让研究者自己补一份声明即可”。

## 8. Research workflow 的使用边界

### Design 前

若伦理、数据保护、监管或许可会决定 sampling / intervention / data access 是否可执行，则在 Design 形成 execution-ready 状态前解决或记录真实 blocker。

### Study / Data 阶段

实际 approval、consent、permit、protocol amendment、data-use restriction 等按真实 provenance 记录；不能回写 Design 伪装事前已知。

### Communication / Submission 阶段

稿件和 submission package 只能陈述已确认事实。缺失的 approval ID、registration、consent、permission 或 restriction 不能由 Communication 猜测；如果它们影响研究合法实施或数据使用，应返回真正的 project / institutional owner，而不是仅润色声明。

## 9. 输出边界

Akira 可以说：

- “根据已确认项目事实，当前官方来源表明该 requirement 可能/已经适用”；
- “适用性仍 unresolved，需要机构/委员会确认”；
- “已提供的正式文件记录了某 approval / waiver / determination”；
- “当前稿件缺少该事实的可核验来源”。

Akira 不应未经正式依据说：

- “你不需要 IRB / REC”；
- “这个研究已经豁免”；
- “这一定符合某地区数据保护法”；
- “伦理上已经批准”；
- “这个 consent 足够”；
- “机构一定会接受这个 submission packet”。

## 10. 完成条件

当 regulated-research authority 会影响当前科研动作时，`research-standards` 至少应确保：

1. authority 来源与职责已核验；
2. applicability 使用真实项目事实，而非 locale / language / filename 等弱线索；
3. unknown 没有被写成 not applicable；
4. waiver / exception route 没有被误写成已获批准；
5. 多 authority 冲突仍并列保留并交给正式 decision maker；
6. 当前规则版本 / effective period 在 material 时已核验；
7. Akira 的输出没有冒充法律意见、IRB/REC decision、institutional authorization 或合规证书。
