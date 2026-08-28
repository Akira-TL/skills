---
name: literature-access
summary: 将论文引用、DOI、PMID、PMCID 或论文页面解析为经过身份核验的可读取全文，并在开放获取、认证访问和动态下载之间按需升级。
description: 用于需要真正取得论文原文而不是只读取标题或摘要的任务。负责文献身份解析、开放全文定位、认证访问交接、PDF 请求解析、内联下载和全文验收；不负责系统综述检索、论文内容总结或浏览器实现细节。
---

# 论文原文获取

本 Skill 的完成条件不是“找到论文页面”，而是得到一个经过身份核验、可由 Agent 读取的全文 artifact。

## 核心边界

- 本 Skill 只处理 **access**：从 citation / DOI / PMID / PMCID / URL 到全文 artifact；已确定论文的 Supplementary Information、Reporting Summary、Source Data、protocol、代码/数据附件也可作为同一论文下的明确 access target。
- 允许为了取得一篇**已经确定身份的目标论文**执行 exact-work resolution search，例如用 DOI、PMID、完整标题或作者 + 年份寻找 publisher、repository、开放副本或全文入口。
- 不负责从研究主题发现候选论文，也不负责筛选、证据抽取、研究笔记、论文关系图或研究项目管理；这些属于上层科研 Skill。
- 优先使用当前环境已有的 WebFetch / HTTP / web search 能力完成直接获取和 resolution search；需要动态页面、用户授权或会话解析时，再把浏览器部分交给当前环境可用的浏览器访问能力。
- 浏览器发现、Profile、登录和人机协作由浏览器能力负责，本 Skill 不复制这些规则。
- 浏览器不承担文件落盘。解析出最终资源请求后，优先由 Agent 直接、内联地传输文件。
- 只使用公开可得版本或用户已有合法权限能够访问的版本。
- **单一资源入口失败不等于全文不可得。** PDF 返回 403、访问挑战页或 HTML 错页时，必须回到论文页面检查网页全文、真实下载请求及附件入口，并继续围绕目标论文进行精确解析检索（exact-work resolution search）；一个 URL 的失败不能直接升级为 `MANUAL_ACQUISITION_REQUIRED`。
- DOI、PMID 或页面元数据若明确暴露 PMCID、Europe PMC、机构知识库（repository）、作者接受稿（accepted manuscript）、预印本（preprint）或其他合法全文位置，这是必须继续跟进的正向线索，不能在未访问该线索时宣称获取失败。
- **需要用户权限或用户文件时必须进入人机协同，而不是放弃。** 如果公开路径没有拿到全文，但出版社、机构或数据库存在登录后可访问的可能性，必须路由到用户授权浏览器访问；优先复用可见、持久的专用浏览器配置（browser profile），由用户亲自完成密码、验证码、机构登录或二次认证，随后继续解析和获取正文。若用户可以从自己有权使用的其他渠道取得论文，也可以请求用户直接提供文件，再执行身份和完整性核验。
- 只要仍在等待用户登录、授权或提供文件，就不能把目标描述为“不可得”，也不能让上层科研项目以该论文已闭合为理由通过完成门禁。

## 按需加载

先读取 [`ROUTER.md`](ROUTER.md)。只读取当前路由需要的节点，不预读整个目录。

## Access State

统一使用以下状态描述当前访问结果：

- `UNRESOLVED`：文献身份尚未确定。
- `IDENTIFIED`：身份已确定，但尚未取得正文。
- `METADATA_ONLY`：只有书目信息。
- `ABSTRACT_ONLY`：只有摘要。
- `OPEN_FULL_TEXT`：已定位公开全文。
- `AUTH_REQUIRED`：需要用户已有的订阅、机构或出版社权限。
- `USER_ACTION_REQUIRED`：需要用户在可见浏览器中完成登录、二次认证或其他人工动作。
- `ARTIFACT_REQUEST_READY`：已经解析出可用于传输全文的资源请求。
- `FULL_TEXT_READY`：全文 artifact 已下载并通过验收。
- `MANUAL_ACQUISITION_REQUIRED`：当前环境无法自行取得全文，需要用户提供文件。

只有 `FULL_TEXT_READY` 才算成功完成。`MANUAL_ACQUISITION_REQUIRED` 表示**机器侧路径已暂时走完、下一步必须由用户协同**，不是“论文不可得”的终态。此状态必须明确请求用户登录、完成授权或提供其合法取得的全文文件；用户尚未回应时，上层研究保持未闭合。

## 失败闭合与 Acquisition Attempt

每一次真实获取/解析尝试都应形成可审计的 Acquisition Attempt，至少包含：

```text
target_kind       -- main_text | supplement | code_data
target_label      -- supplement/code-data target 时标明具体附件
route_family      -- publisher | open_index | repository | preprint | authenticated | other
resource_kind     -- article_page | full_text_html | pdf | xml | repository_record | supplement | other
source_url
outcome           -- acquired | not_found | access_denied | auth_required | challenge | invalid_artifact | network_error | other_failure
detail
attempted_at
access_basis      -- 成功获取时说明出版社开放、公共/机构知识库、作者公开稿、预印本、用户认证或用户提供
access_basis_detail
```

“能够从互联网下载”不等于“可作为规范科研获取来源”。若只找到来源授权关系不明的个人站点、普通镜像或转载文件，即使 DOI、标题和正文边界匹配，也不得把它作为自动获取成功闭合；继续查找正式开放版本、知识库、作者公开稿或预印本。若正式路径需要权限，则进入用户协同；若用户直接提供全文文件，则按 `user_provided` 记录并做论文身份与完整性核验。

对正文宣称“不可得”前，至少必须完成 **publisher 路径 + 一个独立开放解析路径**（open index / repository / preprint）；有 DOI 时 publisher 路径不可跳过。若 publisher PDF 被拒绝或返回 challenge，还必须另查 publisher article page / HTML full text，而不能把 PDF endpoint 当作整个 publisher route。发现新的 repository/PMCID/full-text URL 后必须实际访问，不能只把它写进失败理由。

对 Supplementary Information 宣称 `access_limited` 时同样不能只凭一个附件 URL 失败；需要尝试替代 representation 或独立 route，并把失败 attempt 返回给上层科研项目持久化。

若后续完整性核验推翻了先前的 access 判断（例如一个看似完整的 publisher HTML 实际只是 subscription preview），必须明确返回“旧成功判断已失效”的 correction，而不是让先前 `acquired` 与新的失败结论同时保持有效。上层科研项目应把该 correction 作为新的 Acquisition Attempt，并结构化 supersede 被推翻的旧 attempt。

## Artifact Request

浏览器或网页解析层若需要把下载交给本 Skill，应尽量返回以下临时请求上下文：

```text
url
method
headers
session_context
referer
content_type
suggested_filename
expires_at
```

只携带实际传输需要的字段。认证 Cookie、token 等会话材料只在当前获取流程中临时使用，不作为科研项目资料持久化。

## 输出契约

完成时返回 acquisition result；它只描述“拿到了哪一份全文”，不创建或更新研究项目记录：

```text
status: FULL_TEXT_READY
identity: DOI / PMID / PMCID / canonical citation
version: version-of-record / accepted-manuscript / preprint / other
source: publisher / repository / preprint / other authorized source
source_url
access_basis: publisher_open / public_repository / institutional_repository / author_manuscript / preprint / authenticated_user / user_provided
access_basis_detail
retrieved_at
artifact: local path or runtime file reference
content_type
access_route: open / authenticated / user_provided
```

如果失败，返回停在哪个 Access State、结构化 `attempts[]`、仍未闭合的正向线索，以及下一步需要什么；不要把摘要伪装成全文。只要仍存在尚未跟进的 PMCID/repository/publisher HTML/附件链接，就不得把结果描述为路径已经穷尽。
