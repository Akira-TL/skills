# 直接获取

优先使用当前环境已有的 WebFetch / HTTP / 文件获取能力直接请求目标页面或全文资源。

判断响应实际提供的是：

- metadata；
- abstract；
- HTML full text；
- PDF / 其他完整正文 artifact。

如果已经得到完整正文，进入 `../verify/ROUTER.md`。如果页面只暴露下载入口而没有稳定资源 URL，进入 `../resource/ROUTER.md`。如果只得到 metadata / abstract 或当前 URL 没有全文，进入 `resolution-search.md`。如果确认受权限限制，进入 `authenticated.md`。
