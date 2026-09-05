# MDPI Fast Path

当 canonical publisher 页面属于 MDPI 时，优先把它当作开放全文来源处理。

1. 从 canonical article page 验证标题、DOI 和期刊信息。
2. 先检查页面直接暴露的 PDF / full-text 资源 URL、HTML 元数据和嵌入资源，不为“下载”而模拟浏览器保存文件。
3. 若资源 URL 可直接解析，建立 Artifact Request 并进入 `../fetch/ROUTER.md`。
4. 若站点结构变化、资源由动态请求生成或 fast path 失败，立即回到 `../resource/ROUTER.md` 的通用解析流程，不硬编码失效的 URL 模板。
