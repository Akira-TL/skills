# Akira Skill 安装契约

本文件只定义 **如何安装与更新 Skill**。安装“什么能力、来自哪个 first-party 产品仓”由 [`CATALOG.md`](CATALOG.md) 决定；外部来源由 [`EXTERNAL-SOURCES.md`](EXTERNAL-SOURCES.md) 决定。

Akira 不依赖第三方 Skill package manager。正式安装入口是 Akira Lattice 自己的：

```bash
python3 ~/.agents/scripts/skills.py --help
```

实现只依赖 Python 标准库与 Git。

## 1. Source 与 Skill view 分离

真正的 Skill 文件只存在于共享 Git checkout：

```text
~/.agents/sources/<owner>/<repo>/
```

安装本身只建立软链接，不复制 Skill 目录。

全局 Skill：

```text
~/.agents/sources/Akira-TL/skills/routing/akira/
        ↓ symlink
~/.agents/skills/akira
        ↓ symlink（ForgeRelay 常驻基线才需要）
~/.forgerelay/skills/akira
```

项目级 Skill：

```text
~/.agents/sources/Akira-TL/akira-research-skills/skills/research/analysis/
        ↓ symlink
<project>/.agents/skills/analysis
```

项目安装不复制到全局 `~/.agents/skills/`，也不因为一个项目的需求污染其他项目。

## 2. 只从远端 Git source 建立或更新 checkout

安装器接受 GitHub HTTPS 或 `git@github.com:` source。首次安装执行 clone；已有 source checkout 时：

1. 核验 `origin` 与请求的 GitHub repository 一致；
2. 检查 checkout 必须 clean；
3. `git fetch --prune origin`；
4. 对 branch ref 重置到对应 `origin/<ref>`；
5. 记录实际 Git commit。

如果 source checkout 有本地修改，安装器 fail closed，不覆盖修改。

Lattice 内的 `skills/akira`、`skills/research`、`skills/matt` submodule 只用于开发、review 与固定 source revision，**不是运行时安装源**。

## 3. 项目级安装是默认方式

安装单个 Skill：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill general-word-document-generation \
  --project /path/to/project
```

安装一个产品目录中的全部 Skill：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/akira-research-skills.git \
  --all \
  --root skills/research \
  --project /path/to/project
```

`--root` 可重复，只影响 `--all` 的发现范围；显式 `--skill` 可以额外加入 root 之外的 Skill。

安装完成后，项目中只有：

```text
<project>/.agents/skills/<name> -> ~/.agents/sources/.../<skill-dir>
<project>/.agents/akira-skills.json
```

manifest 保存 repository、ref、实际 commit、source-relative path 与安装 scope；它不复制 Skill 正文。

## 4. 全局安装只用于明确的跨项目基线

普通 Research、Matt、Word、PPT 等能力不全局安装。

只有明确的跨项目常驻能力使用 `--global`：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill akira \
  --skill browser-access \
  --global \
  --forgerelay
```

这会建立：

```text
~/.agents/skills/akira          -> ~/.agents/sources/Akira-TL/skills/routing/akira
~/.agents/skills/browser-access -> ~/.agents/sources/Akira-TL/skills/productivity/browser-access

~/.forgerelay/skills/akira          -> ~/.agents/skills/akira
~/.forgerelay/skills/browser-access -> ~/.agents/skills/browser-access
```

`--forgerelay` 只允许与 `--global` 一起使用。ForgeRelay view 始终链接到全局 `.agents/skills`，不直接链接 source checkout。

## 5. 更新只更新 Git checkout

项目级：

```bash
python3 ~/.agents/scripts/skills.py update --project /path/to/project
```

全局：

```bash
python3 ~/.agents/scripts/skills.py update --global
```

只更新某个 repository：

```bash
python3 ~/.agents/scripts/skills.py update \
  --project /path/to/project \
  --source https://github.com/Akira-TL/akira-research-skills.git
```

因为 Skill view 是软链接，checkout 更新后所有已安装 view 立即读取新内容；无需重新复制 Skill。

## 6. 卸载只删除受管软链接

删除单个项目 Skill：

```bash
python3 ~/.agents/scripts/skills.py remove analysis --project /path/to/project
```

删除同一 source 在当前项目安装的全部 Skill：

```bash
python3 ~/.agents/scripts/skills.py remove \
  --source https://github.com/Akira-TL/akira-research-skills.git \
  --project /path/to/project
```

安装器只删除 manifest 中登记且仍指向预期 source 的软链接。普通目录、指向其他 source 的软链接和未知文件 fail closed。

卸载不自动删除 `~/.agents/sources/` checkout；多个项目可以共享同一个 source cache。

## 7. Doctor 与清单

查看当前项目受管 Skill：

```bash
python3 ~/.agents/scripts/skills.py list --project /path/to/project
```

机械验证 source 与软链接：

```bash
python3 ~/.agents/scripts/skills.py doctor --project /path/to/project
```

全局基线：

```bash
python3 ~/.agents/scripts/skills.py list --global
python3 ~/.agents/scripts/skills.py doctor --global
```

Doctor 至少验证：

- source Skill 仍存在 `SKILL.md`；
- `.agents/skills/<name>` 是软链接且直接指向登记的 Git checkout 路径；
- 全局 manifest 中标记为 ForgeRelay 的 Skill，其 `~/.forgerelay/skills/<name>` 是软链接且指向 `~/.agents/skills/<name>`。

## 8. 不做的事情

Akira Skill installer 不实现 dependency solver、包仓库、自动 Agent profile 检测、copy fallback 或隐式全局扩张。

它不：

- 复制 Skill 目录；
- 把项目 Skill 自动升级成全局 Skill；
- 在 symlink 失败时悄悄退化为 copy；
- 自动删除未知目录；
- 用本地 Lattice submodule 代替远端发布 source；
- 因 source repository 新增实验 Skill 而自动把它安装到已有项目。

需要新增能力时，由 Catalog / External Sources 决定具体 source 与 Skill 集合；安装器只机械执行 Git + symlink。
