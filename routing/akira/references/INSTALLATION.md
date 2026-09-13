# Akira Skill 安装契约

本文件只定义 **Akira 如何把 Skill 安装到机器级注册表**。安装“什么能力、来自哪个 first-party 产品仓”由 [`CATALOG.md`](CATALOG.md) 决定；外部来源由 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md) 决定。

安装能力由 `akira` Skill 自己拥有，不由 Akira Lattice 根仓提供，也不依赖第三方 Skill package manager。正式入口是本 Skill 自带脚本：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py --help
```

实现只依赖 Python 标准库与 Git。Router 已经可用后，Agent 在确认能力缺口并获得用户授权时主动调用该脚本；`akira` 本体的首次 bootstrap 不由自身安装器处理。

## 1. 运行时只有 source 与机器级注册表

真正的 Skill 文件只存在于共享 Git checkout：

```text
~/.agents/sources/<owner>/<repo>/
```

机器上已经安装的 Skill 统一注册到：

```text
~/.agents/skills/<skill>
```

注册项始终是软链接：

```text
~/.agents/sources/<owner>/<repo>/<skill-dir>
        ↓ symlink
~/.agents/skills/<skill>
```

Skill 内容不复制，Git checkout 是唯一实体。

机器级安装状态记录在：

```text
~/.agents/akira-skills.json
```

manifest 保存 repository、ref、实际 commit 与 source-relative path，用于更新、诊断和同名冲突检查。

## 2. Agent 先发现，再安装

需要某个 Skill 时按以下顺序处理：

1. 先检查当前会话是否已经真实可用；可用则直接使用。
2. 当前会话不可用时，检查 `~/.agents/skills/<name>`；如果它是 Akira manifest 登记的有效机器级 Skill，不重复安装。
3. 机器级注册表也不存在时，才按 Catalog 登记或用户明确批准的 GitHub source 安装。

机器级 Skill 安装完成后，执行器若需要自己的 Skill 目录，由执行器自己建立 `<executor-skill-dir>/<name> -> ~/.agents/skills/<name>` 软链接。Akira 安装器不规定任何具体执行器的运行时目录，也不创建、更新或删除这些执行器链接。

同名 Skill 如果已经由其他 repository 注册，安装器 fail closed；不得静默改写机器级名称指向。

## 3. 只从远端 Git source 建立或更新 checkout

安装器接受 GitHub HTTPS 或 `git@github.com:` source。需要远端安装或更新时：

1. 首次安装执行 clone；
2. 核验 `origin` 与请求的 GitHub repository 一致；
3. 检查 checkout 必须 clean；
4. `git fetch --prune origin`；
5. 对 branch ref 重置到对应 `origin/<ref>`；
6. 记录实际 Git commit。

如果 source checkout 有本地修改，安装器 fail closed，不覆盖修改。

Lattice 内的 `skills/akira`、`skills/research`、`skills/matt` submodule 只用于开发、review 与固定 source revision，**不是运行时安装源**。

## 4. 默认安装到 `~/.agents/skills`

安装单个 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill general-word-document-generation
```

安装一个产品目录中的全部 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/akira-research-skills.git \
  --all \
  --root skills/research
```

`--root` 可重复，只影响 `--all` 的发现范围；显式 `--skill` 可以额外加入 root 之外的 Skill。

安装完成后只新增或更新：

```text
~/.agents/sources/<owner>/<repo>/
~/.agents/skills/<name>
~/.agents/akira-skills.json
```

不会自动创建项目级 Skill 目录，也不会修改任何具体执行器的 Skill store。

## 5. Inspect

外部或新 source 在安装前先检查：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py inspect <github-url>
```

`inspect` 只 clone/fetch source cache 并扫描 `SKILL.md`，不创建 `~/.agents/skills` 注册项。

## 6. Update

更新全部机器级受管 Skill 的 source：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py update
```

只更新某个 repository：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py update \
  --source https://github.com/Akira-TL/akira-research-skills.git
```

因为机器级注册项是软链接，checkout 更新后注册表立即读取新内容。

## 7. Remove

删除单个机器级注册项：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py remove analysis
```

删除某个 source 登记的全部 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py remove \
  --source https://github.com/Akira-TL/akira-research-skills.git
```

安装器只删除 manifest 中登记且仍指向预期 source 的机器级软链接。普通目录、未知软链接和来源漂移都 fail closed。

删除注册项不会删除 `~/.agents/sources/` checkout，也不替具体执行器清理它自己的引用或缓存。

## 8. Doctor 与清单

查看机器级已安装 Skill：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py list
```

机械验证 source 与注册表：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py doctor
```

Doctor 至少验证：

- source Skill 仍存在 `SKILL.md`；
- `~/.agents/skills/<name>` 是软链接且直接指向 manifest 登记的 Git checkout 路径；
- 注册表中不存在未登记的受管名称冲突。

## 9. 执行器边界

Akira Skill installer 不实现执行器适配层。它不决定：

- 具体执行器从哪个目录加载 Skill；
- Claude Code 如何发现或链接 Skill；
- Codex 如何注册或暴露 Skill；
- 某个执行器是否需要项目级链接、自己的 manifest、缓存或 profile。

这些都由对应执行器自己的配置与能力机制负责。`~/.agents/sources/` 是唯一受管 source checkout，`~/.agents/skills/` 是唯一机器级注册表；执行器自己的 Skill 目录只作为软链接视图，不维护第二份 source checkout。

## 10. 不做的事情

Akira Skill installer 不实现 dependency solver、包仓库、自动 Agent profile 检测或 copy fallback。

它不：

- 复制 Skill 目录；
- 在 symlink 失败时悄悄退化为 copy；
- 自动覆盖机器级同名 Skill 的其他来源；
- 自动删除未知目录；
- 用本地 Lattice submodule 代替远端发布 source；
- 因 source repository 新增实验 Skill 而自动把它加入机器级注册表；
- 管理任何具体执行器自己的 Skill 目录。

需要新增能力时，由 Catalog / External Sources 决定具体 source 与 Skill 集合；安装器只机械执行 Git checkout 与机器级注册。
