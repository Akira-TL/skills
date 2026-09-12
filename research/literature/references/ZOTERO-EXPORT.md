# Zotero 推荐阅读出口

本文件只负责把 **Akira 已经推荐给用户亲自阅读的论文**送入 Zotero，方便用户在人类文献管理器里阅读和自行整理。Zotero 不成为 Akira 的第二套科研状态源。

## 1. 默认出口

默认目标是用户个人 Zotero Library 中的顶层 collection：

```text
Akira Recommended Reading
```

默认候选来自项目 `research.sqlite` 中：

```text
relevance_status = relevant
reading_priority ∈ {core, high}
```

这表示“Agent 推荐用户优先阅读”，不表示用户已经读过、确认过或同意论文结论。

Akira 只负责把推荐项放入这个固定 collection。之后用户希望按课题、章节、方法、已读/待读或任何私人体系整理时，由用户自己在 Zotero 中拖拽；Agent 不继续创建层层子 collection、重命名用户现有 collection、批量移动用户条目或维护个人标签体系。Zotero collection 本身允许同一 item 同时属于多个 collection，因此用户后续拖入自己的 collection 不需要复制科研条目。

## 2. Zotero 支持范围

优先使用 Zotero 10+ 官方 Local API：

```text
http://localhost:23119/api/
```

只允许：

- probe 当前 Local API 是否真实可达；
- 读取当前 user library 的 collection / item metadata 用于去重；
- 请求 Zotero 自己的 write authorization；
- 创建 `Akira Recommended Reading` collection（不存在时）；
- 创建推荐阅读 bibliographic items；
- 对已经存在的同一 DOI / title-year item，仅把它加入该 collection。

禁止：

- 直接写 `zotero.sqlite`；
- 用浏览器 / GUI 自动化模拟点击 Zotero；
- 为了“找到 Zotero”扫描端口、猜 Windows host IP 或尝试未确认的内部接口；
- 修改用户其他 collection、tag、note、attachment 或 citation state；
- 自动上传 Akira 本地 PDF / Supplement 到 Zotero；
- 把 Zotero 的 read/unread、collection 或 note 当作 Akira canonical Literature 状态。

## 3. Fail-closed：每次调用都有固定尝试预算

Agent 只有在用户明确要求“导出 / 同步推荐阅读到 Zotero”时才运行脚本；`reading_priority` 改变本身不触发后台写入。

一次脚本调用：

1. Local API **只 probe 一次**；
2. 已有 remembered local key 可用则复用；
3. 没有可用 key 时，最多请求 **一次** Zotero 官方授权弹窗；
4. `403`、用户 Deny、`429`、连接失败、版本/接口不支持或其他写入错误后，不循环重试；
5. 立即保留/生成标准 RIS fallback，并告诉用户当前没有直接写入；
6. 如果 collection 不存在且本次用户只选择一次性 `Allow`，创建 collection 会消耗一次性 key；脚本此时不弹第二次授权，保留 RIS 并结束。用户下次再运行即可写 items，或可在 Zotero 授权框选择 `Always Allow`。

如果运行环境是 WSL，而 Windows 上的 Zotero Local API 没有通过当前网络模式暴露到 WSL 的 `localhost`，这属于环境边界。脚本不自行绕过；用户可以显式传入其已确认可用的 `--base-url`，否则使用 RIS fallback。

## 4. 授权与缓存

Zotero Local API write key 由 Zotero 运行时授权产生，不等同于 zotero.org Web API key。

- 用户选择一次性 `Allow`：key 只用于当前允许的首次 write；不持久化。
- 用户选择 `Always Allow`：脚本可以把返回的 remembered key 与 `Zotero-Server-ID` 保存在用户级配置 `~/.config/akira/zotero-local.json`（权限 `0600`），不写入科研项目、Git、`research.sqlite` 或日志。
- Server ID 变化、key 返回 `401` 或用户清除 Zotero write authorization 后，旧 key 失效并从缓存移除。

输出和日志不得显示 key。

## 5. 去重与条目边界

直连 Zotero 前先读取当前 library metadata：

- DOI 相同 → 视为同一 scholarly work；只把现有 item 加入 `Akira Recommended Reading`；
- DOI 缺失时，只有规范化 title + year 足够一致才作为保守 fallback；
- 不能可靠判断同一性时，新建 item，不通过模糊作者关键词合并；
- 不调用 Zotero 的“Merge Duplicates”替用户整理整个库。

Akira 导出的 bibliographic metadata 只来自当前 Candidate / Paper 已有字段。缺失 journal、author、DOI 等保持缺失，不上网临时猜补后直接写进 Zotero；若需要完善 metadata，先在 Literature canonical workflow 中完成 identity resolution。

## 6. RIS fallback

无论是否直连成功，脚本都可以生成：

```text
.research/exports/zotero/Akira Recommended Reading.ris
```

Zotero 官方支持 RIS / BibTeX / CSL JSON 等标准格式导入。RIS fallback 是人类协同入口，不是新的科研 source of truth。用户可以在 Zotero 选中希望放置的 collection 后导入 / 从剪贴板导入，再自行拖拽整理。

## 7. 脚本

使用：

```bash
python <literature-skill>/scripts/zotero_export.py --project-root <research-project>
```

常用参数：

```text
--collection <name>      # 默认 Akira Recommended Reading
--priorities core,high   # 默认推荐阅读等级
--file-only              # 只生成 RIS，不尝试 Local API
--base-url <url>         # 仅使用用户/环境已经确认的 Local API 地址
```

脚本的 stdout 输出结构化 summary，供 Agent 判断是 `pushed`、`fallback_only`、`collection_created_only` 还是 `no_recommendations`。Agent 必须按实际状态回复，不能把“生成 RIS”说成“已经写入 Zotero”。