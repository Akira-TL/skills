# Literature Access Router

按当前缺失的信息只读取下一跳。

- 文献身份不确定、只有标题/引用或多个候选：读取 [`identity/ROUTER.md`](identity/ROUTER.md)。
- 已确定目标文献，尚未取得全文：读取 [`access/ROUTER.md`](access/ROUTER.md)。
- 已打开目标页面，需要解析真正的 PDF/全文请求：读取 [`resource/ROUTER.md`](resource/ROUTER.md)。
- 已取得 Artifact Request，需要传输文件：读取 [`fetch/ROUTER.md`](fetch/ROUTER.md)。
- 已有 PDF/全文文件，需要确认是否真的是目标全文：读取 [`verify/ROUTER.md`](verify/ROUTER.md)。

不要因为后续节点可见而预读；每个 Router 只负责当前下一跳。
