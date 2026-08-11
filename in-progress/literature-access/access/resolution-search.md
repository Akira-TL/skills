# 获取型搜索

只围绕已经确定 canonical identity 的目标论文搜索可获取副本或全文入口。优先使用 DOI、PMID / PMCID、完整标题，必要时加作者与年份消歧。

可使用当前环境已有的 web search、WebFetch、HTTP 或站点检索能力查找：

- publisher article / PDF 页面；
- PubMed Central / Europe PMC 等全文入口；
- 机构 repository；
- 作者公开的 accepted manuscript；
- 与正式论文身份明确关联的 preprint。

搜索结果必须回到 canonical target 做身份核验。不要从主题关键词扩展候选论文，也不要在这里执行综述检索、筛选或研究问题发现。

找到公开候选时进入 `open-copy.md`；只找到需要登录的 publisher / institution 入口时进入 `authenticated.md`；没有可行候选则返回 `MANUAL_ACQUISITION_REQUIRED`。
