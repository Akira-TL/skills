# 解析论文身份

目标是建立一个 canonical identity，而不是尽可能多抄 metadata。

优先确认：

1. DOI；
2. PMID / PMCID（生命科学论文存在时）；
3. canonical title；
4. first / corresponding author；
5. year 与 journal。

可以使用当前环境已有的 web search、WebFetch、HTTP 或书目数据库查询能力，只为解析这一篇目标论文的 canonical identity；不要从主题关键词扩展成候选文献发现。

用至少两个互相一致的高置信字段排除同名、预印本/正式版混淆和相似标题。若 preprint 与正式发表版都存在，记录版本关系，并优先把正式发表版作为 canonical identity；获取全文时可以使用合法开放的作者稿或预印本，但必须保留版本信息。

身份确定后返回 `IDENTIFIED`。
