# Docs-first Analysis

分析工具的 API、默认参数和统计语义会随版本变化。遇到任何会影响结果的未知或不确定项，按以下证据顺序确认：

1. 当前实际安装版本；
2. 本地 `--help`、package help、函数签名与 bundled vignette；
3. 对应版本的官方 documentation / vignette；
4. 方法论文或维护者发布的权威说明；
5. 只有前述来源仍不能回答时，才使用二级教程或社区讨论辅助定位，并回到原始来源核验。

必须核验的典型事项：

- 默认 normalization / transformation / correction；
- 输入数据类型与允许的预处理；
- reference level、contrast、factor coding；
- multiple-testing correction；
- missing value / zero / pseudocount 行为；
- random seed、split、cross-validation；
- feature importance 或 effect-size 定义；
- database / annotation release；
- 已弃用参数和版本间行为变化。

记录**会改变结果解释**的版本与参数，不复制整页文档。若文档与实际行为不一致，先建立最小可复现实验确认，再把差异记录为 execution issue。
