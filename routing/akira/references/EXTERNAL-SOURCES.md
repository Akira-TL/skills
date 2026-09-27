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

- Source：`https://github.com/op7418/Humanizer-zh.git`
- Owner：`op7418`
- Intended Skill：`humanizer-zh`
- License：MIT
- Lattice pin：no
- 默认安装：no
- 当前 first-party consumer：`scientific-presentation-authoring`

`humanizer-zh` 只在科研 PPT 的中文页面文案终检分支中使用，不拥有科研事实、统计结果、术语、证据强度或演示结构。

窄调用契约：只允许清理机械排比、宣传式大词、空泛意义句、翻译腔、过度连接词及其他 AI 写作模式；不得借此新增第一人称、个人观点、幽默、情绪、轶事、新例子、新事实或更强科学结论。

### 当前 Skiloom compatibility

2026-09-27 对 upstream Git `main` 的实际 Skiloom Candidate plan 返回：

```text
InvalidSkillPackage
reason: invalid-allowed-tools
```

因此当前 upstream 不能作为 Skiloom-accepted Package 安装。进入中文终检分支时：

- 当前会话已经具备该能力 → 可以按窄调用契约使用；
- 当前 Target 没有且 upstream 仍不能通过 Skiloom admission → 明确报告 Humanizer 终检 blocker；
- 不得调用旧 Akira installer 绕过 admission；
- 若以后 upstream 修复或我们明确决定维护兼容 Package，重新执行 Skiloom plan 后再更新本状态。

## 其他外部来源

其他第三方来源只有在来源、license、执行副作用、数据边界与 Skiloom Package compatibility 已经核验后才加入本表。记录来源不等于授权安装。
