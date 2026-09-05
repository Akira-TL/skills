# 直接内联传输

使用当前 Agent 环境的 HTTP / download 能力直接请求 Artifact Request URL，并把响应保存到当前任务可访问的位置。

遵循 redirect，保留最终 URL 和响应 content type。文件名优先来自可靠的响应头或 canonical identity，而不是盲信 URL 尾部。

下载完成不等于成功；立即进入全文验收。
