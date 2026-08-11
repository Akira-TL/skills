# Identity Router

- 只有 citation、标题、作者、年份或网页：读取 [`resolve.md`](resolve.md)。
- 已经有可信 DOI、PMID 或 PMCID，且标题/作者基本一致：返回 `IDENTIFIED`，进入 `../access/ROUTER.md`。
- 多个候选无法唯一确定：保持 `UNRESOLVED`，先补足身份信息，不继续下载。
