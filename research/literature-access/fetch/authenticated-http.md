# 认证请求内联传输

使用 Artifact Request 中必要的临时 headers、referer、cookie/session context 重放全文请求，并由 Agent 自己保存响应。

只复现取得目标 artifact 所需的最小请求上下文。若返回登录页、403、HTML challenge 或其他非正文响应，不反复猜测认证参数；改走 `browser-context.md` 或重新交给浏览器访问能力刷新授权。
