# 外部 Skill 能力源

本文件只记录经过确认、但不由 Akira 维护的 Skill 来源。外部来源不是 Lattice submodule，也不因为出现在本表就获得自动安装权限。

## OpenAI Plugins

- Source：`openai/plugins`
- Owner：OpenAI
- Status：official upstream
- Lattice pin：no
- 默认安装：no
- 用途：OpenAI 官方维护的专业插件与领域 Skill 集合，包括生命科学、开发、设计、文档与第三方服务等能力。

Router 不在本仓库复制 OpenAI Plugins 的完整 Skill 清单，因为 upstream 会持续变化。需要判断当前有哪些可安装能力时，读取官方当前来源并使用 skills CLI 的只读列表入口：

```bash
npx skills add openai/plugins --list
```

只把与当前任务直接相关的候选 Skill 告诉用户，不把整个 upstream 仓库加入项目。准备安装具体 Skill 前，至少确认：

- 当前候选 Skill 的准确名称和用途；
- 是否包含脚本、网络访问、账户、凭据、外部 API、云执行或数据上传；
- 是否会读取当前项目数据，以及数据是否可能离开本机；
- 当前项目是否已经存在足够能力；
- 安装范围是否保持为当前项目。

用户明确同意后，只安装实际需要的 Skill：

```bash
npx skills add openai/plugins --skill <skill-name> --agent '*' -y
```

不得因为 OpenAI 是官方来源就自动安装、全局安装或默认信任其中所有执行动作。

### 与 Akira Research 的关系

Akira Research 的 `ngs` 仍拥有高通量测序任务的科研语义、数据/分析边界和 provenance；OpenAI Plugins 中的 NGS 相关能力只作为可选执行来源。需要 NGS runner 或 assay-specific guidance 时，先通过当前 OpenAI Plugins 清单定位最窄能力，再按上述审计和用户授权流程项目级安装。Research 不要求 Lattice 预先固定整个 `openai/plugins` 仓库。

## 其他外部来源

其他第三方 Skill 来源只有在已经完成来源、license、执行副作用和数据边界审计后，才可以加入本表。加入本表不等于加入默认安装集，也不等于允许 Router 无确认执行安装。
