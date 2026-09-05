# 直接获取

优先使用当前环境已有的 WebFetch / HTTP / 文件获取能力直接请求目标页面或全文资源。

判断响应实际提供的是：

- metadata；
- abstract；
- HTML full text；
- PDF / 其他完整正文 artifact。

如果已经得到完整正文，进入 `../verify/ROUTER.md`。如果页面只暴露下载入口而没有稳定资源 URL，进入 `../resource/ROUTER.md`。如果只得到 metadata / abstract 或当前 URL 没有全文，进入 `resolution-search.md`。如果确认受权限限制，进入 `authenticated.md`。

直接 PDF/附件请求若返回 403、challenge 页面、HTML 错页或其他无效 artifact，必须把这次真实请求记录为 Acquisition Attempt，然后回到论文 article page 检查 HTML full text、下载控件与附件链接，再进入 `resolution-search.md` 寻找独立开放路径。不得由一个失败资源 URL 推断整篇论文或附件不可获取。
