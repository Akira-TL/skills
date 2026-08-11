# Access Router

按成本从低到高获取全文：

1. 已知 publisher / repository / full-text URL 可直接访问：读取 [`direct.md`](direct.md)。
2. 直接页面只有 metadata/abstract 或 paywall：读取 [`open-copy.md`](open-copy.md)。
3. 没有公开全文，但用户可能拥有机构、订阅或出版社权限：读取 [`authenticated.md`](authenticated.md)。
4. 当前环境既无公开版本，也无法使用用户授权访问：返回 `MANUAL_ACQUISITION_REQUIRED`，请求用户提供 PDF 或合法可访问链接。

若目标来自 MDPI，可先读取 [`../providers/mdpi.md`](../providers/mdpi.md) 走 provider fast path；失败后回到本 Router 的通用路径。
