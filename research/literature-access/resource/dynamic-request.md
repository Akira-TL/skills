# 动态资源请求

如果资源只有触发页面动作后才能解析，浏览器动作的目的仅是**暴露真实网络请求**。

在触发动作前开启当前浏览器能力支持的网络观察。随后触发 PDF / Full Text 动作，捕获：

- 最终 request URL；
- redirect 后 URL；
- method；
- 必需 headers；
- response content type；
- 必要的临时 session context。

识别出目标资源后建立 Artifact Request。浏览器自身的默认下载不是成功条件；文件传输交给 `../fetch/ROUTER.md`。
