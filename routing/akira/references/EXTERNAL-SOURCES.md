# 外部 Skill 能力源

本文件记录经过确认、但不由 Akira 维护的外部来源与额外审计边界。出现在本表不等于 Package 已被 Skiloom 接受，也不等于获得自动安装权限。

所有外部 Skill 生命周期动作同样只允许走 Skiloom。Akira 不再提供绕过 Package admission 的 Git + symlink 安装路径。

## 通用流程

1. 先确认 first-party 能力确实不足。
2. 使用 `skiloom-discover` / `skiloom search "<query>" --json` 发现当前候选。
3. 核对候选来源、用途、脚本/网络/账户/凭据/云执行/数据上传副作用。
4. 用户选定后收敛为明确 Package coordinate 与 source mode。
5. 先执行 `skiloom install ... --plan --json`；Package admission 或 source resolution 不通过时保持 blocker。
6. 用户明确授权后才使用 `--yes --json` 提交。

Catalog/provider metadata 只用于发现，不替代 GitHub source authority、exact commit、content digest 或 Candidate acceptance。

## OpenAI Plugins

- Source family：`openai/plugins`
- Owner：OpenAI
- Status：official upstream discovery source
- Lattice pin：no
- 默认安装：no

需要 OpenAI Plugins 中的专业能力时，不在 Akira 仓库复制 upstream 的完整 Skill 清单。通过 Skiloom discovery 获取当前候选，只继续评估与当前任务直接相关的 Package。

准备安装前至少确认：

- 准确 Package identity 与用途；
- 是否包含脚本、网络访问、账户、凭据、外部 API、云执行或数据上传；
- 是否会读取当前项目数据，以及数据是否可能离开本机；
- 当前 Target 是否已经存在足够能力；
- Candidate plan 的 exact source、dependency graph、projection 与 warning。

不得因为 OpenAI 是官方来源就自动批准状态变化。

### 与 Akira Research 的关系

Akira Research 的 `ngs` 仍拥有高通量测序任务的科研语义、数据/分析边界和 provenance；外部 NGS Package 只作为可选执行能力。Research 只声明能力缺口，由 `akira` Router 与 Skiloom 处理发现和生命周期。

## Humanizer-zh

- Source：`https://github.com/ai-zixun/humanizer-zh.git`
- Owner：`ai-zixun`
- Package coordinate：`ai-zixun/humanizer-zh/humanizer-zh`
- Preferred source：GitHub Release `v1.3.0`
- License：MIT
- Default scope：`user`
- Lattice pin：no
- 默认安装：no
- 当前 first-party consumer：`scientific-presentation-authoring`

`humanizer-zh` 是可选中文语言 QA，不是科研 PPT 的完成门禁。科研 PPT 即使不安装 Humanizer，也必须依靠 first-party 规则完成事实、术语、证据强度、结果/解释边界和基础语言清理；只有需要额外处理翻译腔、机械排比、空泛大词、口号式收束或段落节奏时，才按需调用 Humanizer。

窄调用契约：

- 只允许清理翻译腔、结构腔、排版腔、机械对照句、空泛结论、过度连接词和其他 AI 式语言模式；
- 必须保留原文事实、数字、统计结果、术语、限定条件、作者立场与信息密度；
- 不得新增第一人称、个人观点、幽默、情绪、轶事、新例子、新事实或更强科学结论；
- 不启用 `v1.3.0` 的可选作者声线 / Voice Adoption；科研与技术材料始终采用中性、克制、可核验表达。

### 当前 Skiloom compatibility

2026-09-28 对正式 GitHub Release 的实际 Candidate plan：

```text
repository: ai-zixun/humanizer-zh
release: v1.3.0
package: ai-zixun/humanizer-zh/humanizer-zh
status: planned
warnings: []
```

因此当前可以直接由 Skiloom Release resolver 管理，不需要跟随 Git `main`：

```text
skiloom install ai-zixun/humanizer-zh/humanizer-zh --scope user --plan --json
```

只有用户明确授权本次状态变化后才提交安装。Humanizer 不可用或用户不愿安装时，继续完成科研 PPT，并如实跳过可选 Humanizer QA；不得把它升级为 blocker。

## 其他外部来源

其他第三方来源只有在来源、license、执行副作用、数据边界与 Skiloom Package compatibility 已经核验后才加入本表。记录来源不等于授权安装。
