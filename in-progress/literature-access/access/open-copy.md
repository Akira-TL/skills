# 定位合法开放全文

对 `resolution-search.md` 找到的合法开放候选做版本与全文核验。不要在本文件扩展主题检索；目标已经由 canonical identity 锁定。

优先级不是固定站点名单，而是“版本身份可靠 + 全文可直接取得”。重点检查：

- 出版社自身开放全文；
- PubMed Central / Europe PMC 等生命科学全文库；
- 机构 repository；
- 作者公开的 accepted manuscript；
- 与正式论文身份明确关联的 preprint。

找到候选全文后先核对 DOI、标题、作者和版本关系，再进入 `../resource/ROUTER.md` 或 `../verify/ROUTER.md`。HTML full text 与经过身份核验的 XML 都是有效正文表示，不应因为 PDF endpoint 受阻而忽略可读取的完整 HTML/XML。

若处理的是 Supplementary Information，必须同时核对 parent paper identity 与附件 label/链接关系；publisher 附件下载失败时继续检查 PMC/Europe PMC、repository 或 article page 暴露的其他附件表示。

若只找到摘要，不改变为全文状态；继续返回 Access Router。
