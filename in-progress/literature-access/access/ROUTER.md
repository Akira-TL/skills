# Access Router

按成本从低到高获取全文：

1. 已知 publisher / repository / full-text URL，可用 WebFetch / HTTP 直接访问：读取 [`direct.md`](direct.md)。
2. 直接访问没有全文或目标入口不明确：读取 [`resolution-search.md`](resolution-search.md)，只围绕 canonical target 做 exact-work web search。
3. 搜索到合法开放候选：读取 [`open-copy.md`](open-copy.md)。
4. 没有公开全文，但用户可能拥有机构、订阅或出版社权限：读取 [`authenticated.md`](authenticated.md)，通过用户可见浏览器请求用户完成登录/认证后继续获取。
5. 机器侧公开与授权路径仍无法形成全文时：返回 `MANUAL_ACQUISITION_REQUIRED`，明确请求用户提供其合法取得的 PDF/全文文件或可访问链接。**这是等待用户协同的状态，不是论文“不可得”的完成状态。**

若目标来自 MDPI，可先读取 [`../providers/mdpi.md`](../providers/mdpi.md) 走 provider fast path；失败后回到本 Router 的通用路径。
