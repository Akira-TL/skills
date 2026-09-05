# 获取型搜索

只围绕已经确定 canonical identity 的目标论文搜索可获取副本或全文入口。优先使用 DOI、PMID / PMCID、完整标题，必要时加作者与年份消歧。

可使用当前环境已有的 web search、WebFetch、HTTP 或站点检索能力查找：

- publisher article page、HTML full text 与 PDF 页面；
- Crossref / PubMed / OpenAlex / Unpaywall 等能够暴露开放位置或 PMCID 的 scholarly/open-access resolver；
- PubMed Central / Europe PMC 等全文入口；
- 机构 repository；
- 作者公开的 accepted manuscript；
- 与正式论文身份明确关联的 preprint。

Resolution search 不是“搜到一个结果就结束”。对已有 DOI 的正文获取失败，至少核对 publisher route 与一个独立开放解析 route；core/high-priority 科研论文尤其不能只试一个 PDF endpoint。若 resolver 返回 PMCID、repository URL 或明确的 full-text location，必须继续实际访问该 location 后才能判定结果。

搜索结果必须回到 canonical target 做身份核验。不要从主题关键词扩展候选论文，也不要在这里执行综述检索、筛选或研究问题发现。

找到公开候选时进入 `open-copy.md`；只找到需要登录的出版社（publisher）或机构（institution）入口时进入 `authenticated.md`。机器侧可用的出版社、开放解析、机构知识库/预印本（repository/preprint）等合法路径均已形成真实获取尝试（Acquisition Attempt），且没有尚未跟进的正向全文线索时，可以返回 `MANUAL_ACQUISITION_REQUIRED`，但必须立即转为用户协同：请求用户在可见浏览器中完成其已有权限的登录，或提供其合法取得的全文文件。用户尚未完成或拒绝该协同时，目标不得闭合为“不可得”。
