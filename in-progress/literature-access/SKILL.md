---
name: literature-access
summary: 将论文引用、DOI、PMID、PMCID 或论文页面解析为经过身份核验的可读取全文，并在开放获取、认证访问和动态下载之间按需升级。
description: 用于需要真正取得论文原文而不是只读取标题或摘要的任务。负责文献身份解析、开放全文定位、认证访问交接、PDF 请求解析、内联下载和全文验收；不负责系统综述检索、论文内容总结或浏览器实现细节。
---

# 论文原文获取

本 Skill 的完成条件不是“找到论文页面”，而是得到一个经过身份核验、可由 Agent 读取的全文 artifact。

## 核心边界

- 本 Skill 只处理 **access**：从 citation / DOI / PMID / PMCID / URL 到全文 artifact。
- 文献检索、筛选、证据抽取和综述属于上层科研 Skill，不在这里完成。
- 浏览器只用于动态页面解析、用户授权访问和资源请求解析；浏览器发现、Profile、登录和人机协作由当前环境可用的浏览器能力负责。
- 浏览器不承担文件落盘。解析出最终资源请求后，优先由 Agent 直接、内联地传输文件。
- 只使用公开可得版本或用户已有合法权限能够访问的版本。

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

只有 `FULL_TEXT_READY` 才算完成。

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

完成时返回：

```text
status: FULL_TEXT_READY
identity: DOI / PMID / PMCID / canonical citation
source: publisher / repository / preprint / other authorized source
artifact: local path or runtime file reference
content_type
access_route: open / authenticated
```

如果失败，返回停在哪个 Access State、已经尝试过哪些合法路径，以及下一步需要什么；不要把摘要伪装成全文。
