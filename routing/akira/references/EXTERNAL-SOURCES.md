# 外部 Skill 能力源

本文件只记录经过确认、但不由 Akira 维护的 Skill 来源。外部来源不是 Lattice submodule，也不因为出现在本表就获得自动安装权限。

## OpenAI Plugins

- Source：`openai/plugins`
- Owner：OpenAI
- Status：official upstream
- Lattice pin：no
- 默认安装：no
- 用途：OpenAI 官方维护的专业插件与领域 Skill 集合，包括生命科学、开发、设计、文档与第三方服务等能力。

Router 不在本仓库复制 OpenAI Plugins 的完整 Skill 清单，因为 upstream 会持续变化。需要判断当前有哪些可安装能力时，用 Akira 自带安装器只读检查当前 GitHub source；这一步只 clone/fetch 到共享 source cache，不建立 Skill 软链接：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py inspect https://github.com/openai/plugins.git
```

只把与当前任务直接相关的候选 Skill 告诉用户，不把整个 upstream 仓库加入项目。准备安装具体 Skill 前，至少确认：

- 当前候选 Skill 的准确名称和用途；
- 是否包含脚本、网络访问、账户、凭据、外部 API、云执行或数据上传；
- 是否会读取当前项目数据，以及数据是否可能离开本机；
- 当前会话或机器级注册表是否已经存在足够能力；
- 安装范围是否只进入机器级 `~/.agents/skills` 注册表。

用户明确同意后，只安装实际需要的 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/openai/plugins.git \
  --skill <skill-name>
```

不得因为 OpenAI 是官方来源就自动安装或默认信任其中所有执行动作；具体执行器如何加载已安装 Skill 由执行器自己负责。

### 与 Akira Research 的关系

Akira Research 的 `ngs` 仍拥有高通量测序任务的科研语义、数据/分析边界和 provenance；OpenAI Plugins 中的 NGS 相关能力只作为可选执行来源。需要 NGS runner 或 assay-specific guidance 时，先通过当前 OpenAI Plugins 清单定位最窄能力，再按上述审计和用户授权流程安装到机器级注册表。Research 不要求 Lattice 预先固定整个 `openai/plugins` 仓库。

## Humanizer-zh

- Source：`https://github.com/op7418/Humanizer-zh.git`
- Owner：`op7418`
- Skill：`humanizer-zh`
- Status：audited external dependency
- License：MIT
- Lattice pin：no
- 默认安装：no
- 当前 first-party consumer：`scientific-presentation-authoring`

`humanizer-zh` 是 `scientific-presentation-authoring` 的显式按需依赖，仅用于中文页面文案完成后的语言终检与自然化润色。它不拥有科研事实、统计结果、术语、证据强度或演示文稿结构；调用后必须保持这些内容不变。

当科研 PPT 任务进入中文文案终检阶段时，先检查当前会话是否已经可用 `humanizer-zh`；不可用时再检查机器级 `~/.agents/skills/humanizer-zh`。只有机器级也缺失时，才向用户说明该依赖的来源、用途与安装范围并取得明确同意，然后通过 Akira 安装器按需安装：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/op7418/Humanizer-zh.git \
  --skill humanizer-zh
```

该依赖不进入 Lattice 基础 bootstrap，也不因为安装 `scientific-presentation-authoring` 而提前安装。若用户不允许安装，则明确报告中文 Humanizer 终检未执行；不得伪装成已经完成该依赖步骤，也不得复制第三方 Skill 正文到 Akira 仓库代替安装。

## 其他外部来源

其他第三方 Skill 来源只有在已经完成来源、license、执行副作用和数据边界审计后，才可以加入本表。加入本表不等于加入默认安装集，也不等于允许 Router 无确认执行安装。
