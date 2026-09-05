# 认证请求上下文

当资源依赖登录态时，只传递复现当前全文请求所必需的临时上下文，例如 Cookie、Referer、Authorization 或 signed query。

这些凭据只允许在当前获取流程中短暂存在：

- 不写入科研项目目录；
- 不写进论文 metadata；
- 不把完整认证上下文塞进 handoff 文档；
- 获取结束后不把它当作可长期复用的 artifact。

长期登录态由浏览器 Profile 管理，不由 literature-access 自建凭据缓存。
