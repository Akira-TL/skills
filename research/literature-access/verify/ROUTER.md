# Verify Router

所有候选全文都必须读取 [`full-text.md`](full-text.md) 验收。

验收通过才返回 `FULL_TEXT_READY`。身份不匹配回 `../identity/ROUTER.md`；只有摘要/登录页/错误页回 `../access/ROUTER.md`；文件损坏则重新获取。
