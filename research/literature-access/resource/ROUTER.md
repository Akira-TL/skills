# Resource Router

目标是得到真正的全文资源请求，而不是点击“Download”后等待浏览器保存。

- DOM、HTML metadata、iframe/embed/object 或页面状态已经暴露稳定 PDF/full-text URL：读取 [`static-url.md`](static-url.md)。
- 只有点击/脚本执行后才生成 signed URL、redirect 或下载请求：读取 [`dynamic-request.md`](dynamic-request.md)。
- 已知资源请求需要认证上下文：同时读取 [`authenticated-request.md`](authenticated-request.md)。

得到 Artifact Request 后进入 `../fetch/ROUTER.md`。
