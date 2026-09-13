---
name: akira
description: 判断当前项目需要哪些 Akira / Matt Skill 能力并保持最小安装；当开始新项目、项目缺少一类能力、用户询问应安装什么 Skill，或任务跨到尚未安装的科研、工程、浏览器、文档、PPT 等能力时使用。
---

# Akira Skill Router

`akira` 是通用能力 Router，不替代 Research、Matt 或其他专业 Skill。它负责根据当前项目持续工作的主要类型和当前真实任务，决定是否需要补装新的 Skill，并把安装范围控制在最小充分集合。

## 1. 先看现有能力

先检查当前会话真实可用能力；当前会话不可用时，再检查机器级注册表 `~/.agents/skills/`。若机器级已经存在同名受管 Skill，不重复安装，由当前执行器按自己的 Skill 机制发现、引用或链接它；只有机器级注册表也没有时，才按 Catalog 从远端 GitHub 安装。

当当前能力不足、用户询问可用 Skill、或需要生成安装命令时，读取 [`references/CATALOG.md`](references/CATALOG.md)。它是 first-party 能力名称、GitHub source、发布状态、安装粒度与推荐命令的唯一 source of truth；不要在本文件里维护第二份能力清单。真正执行安装、更新、卸载或诊断时，再读取 [`references/INSTALLATION.md`](references/INSTALLATION.md) 的 Git + symlink 契约。若 first-party 能力仍不足，再读取 [`references/EXTERNAL-SOURCES.md`](references/EXTERNAL-SOURCES.md) 判断是否存在经过登记的外部能力源。

完成标准：能够根据 Catalog 说明当前任务缺的是“通用单一能力”“完整产品域”，还是“需要从登记外部源发现具体 Skill”。

## 2. 优先补单一通用能力

任务只缺一个跨领域能力时，先从 Catalog 的“Akira 通用 Skills / 快速选择表”选择最小 Skill，不安装完整专业产品仓。其他通用能力只有在真实任务需要时才按 Catalog 的准确名称和来源安装。

## 3. 完整产品域才安装产品仓

只有当前项目的主要持续工作需要一整套内部协作能力时，才按 Catalog 推荐完整产品仓。产品的准确 GitHub source、Primary Router、当前状态和安装命令全部以 Catalog 为准，不在本文件重复维护。

完整产品仍然按真实需求才安装；安装器把远端 GitHub source 更新到共享 checkout，并把选中的 Skill 注册到机器级 `~/.agents/skills/`。当前执行器如何加载这些 Skill 由执行器自己负责。跨域需求出现时再增加第二个产品，不因“可能以后用到”预装。

## 4. 外部能力只按当前清单发现

当受管 first-party 能力不足，而 `EXTERNAL-SOURCES.md` 已登记合适来源时，按该来源的当前官方清单发现候选 Skill。不要把外部仓作为 Lattice submodule、不要缓存整仓正文，也不要根据旧会话记忆猜 Skill 名称。

只把与当前任务直接相关的候选、执行副作用和数据边界告诉用户。外部来源即使由可信组织维护，也仍需要用户明确同意后才能安装到机器级注册表。

## 5. 安装必须先获得用户同意

准备安装尚未存在的 Skill / 产品仓时，先向用户说明：

```text
来源仓库
当前任务为什么需要
计划安装的 Skill 或完整产品族
安装范围：机器级 Skill 注册表
当前发布状态
```

用户明确同意后才能执行。准确 GitHub source 与 Skill 集合从 Catalog 读取，安装语义从 `INSTALLATION.md` 读取，不凭记忆拼仓库名、Skill 名称或安装参数。安装后要核验机器级 `~/.agents/skills/<name>` 指向共享 Git checkout，全程不复制目录；执行器自己的 Skill 引用不属于本 Router 的安装契约。若目标处于 `remote-pending`、`planned` 或其他不可直接取得状态，保持 blocker，不把未来仓库伪装成已发布来源。

## 6. 安装后交给真实 Owner

安装成功后只核验所需 Skill 确实出现，然后按 Catalog 记录的 Primary Router / Owner 交接。`akira` 不接管专业产品内部工作，也不复制其路由规则。

后续出现新的能力缺口时重新走本 Router；已经安装某个产品不授权自动扩张其他产品。
