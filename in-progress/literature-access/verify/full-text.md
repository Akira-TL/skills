# 全文验收

至少验证四件事：

1. **文件可读**：PDF/HTML 结构正常，不是空文件或损坏响应。
2. **内容类型真实**：不能只看扩展名；避免把登录页、403 HTML 或 challenge 页面保存成 `.pdf`。
3. **论文身份一致**：标题、DOI、作者、期刊等足以确认它就是 canonical target。
4. **确实是全文**：正文主体存在，而不是 abstract-only、supplement-only、目录页或单独的 graphical abstract。

若是 accepted manuscript、preprint 或其他非 Version of Record 版本，保留版本标记；只要身份关系可靠且全文完整，可以继续验收。

验收通过后记录本次获取本身的 provenance：实际 `source_url`、获取时间、版本、内容类型和 artifact 的 SHA-256。这里只返回 acquisition result，不创建研究笔记、Paper ID、引用关系或科研项目目录结构。

完成后返回 `FULL_TEXT_READY`。
