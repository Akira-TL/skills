# 静态资源 URL

优先从页面结构直接解析全文资源：

- `<a href>`；
- `iframe src`；
- `embed src`；
- `object data`；
- citation / PDF metadata；
- 页面内 JSON 或脚本状态中的资源字段。

把解析到的 URL 规范化为 Artifact Request。不要先让浏览器产生下载文件再去 Downloads 目录查找。
