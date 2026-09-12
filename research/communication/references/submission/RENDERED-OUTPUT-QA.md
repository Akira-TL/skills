# Rendered Output QA

本文件用于科研稿件、Supplement、response package、poster、report 等已经进入正式可交付格式时的**渲染后质量验收**。核心原则是：

> source file 能编译、结构正确或文本审计通过，不等于最终读者看到的页面正确。正式交付应以实际 rendered artifact 为最终检查对象。

本规则只定义跨格式的完成门禁。DOCX、PPTX、PDF / LaTeX 等具体生成和排版技术仍由相应文档 / 演示 / PDF 工具或 Skill 负责，不在 Communication 中维护第二套格式引擎。

## 1. 什么时候必须运行

以下场景在最终交付前运行：

- manuscript / thesis / report 已转换成 DOCX 或 PDF；
- LaTeX / Typst / Quarto / Markdown 等 source 已编译成 submission PDF；
- Supplement / Appendix / response letter 已形成正式页面；
- clean / marked manuscript 已生成最终文件；
- poster / presentation 等页面型传播产物已实际生成；
- 最后一次正文、Figure、Table、citation、cross-reference 或 page-layout 修改之后。

如果用户只要求纯文本草稿、outline 或 source code，并未要求正式页面文件，可以不强制渲染；但不能把未渲染 source 宣称为“最终排版已验收”。

## 2. Source correctness 与 rendered correctness 分开

至少区分两层：

### 2.1 Source / build correctness

检查：

- build / conversion 是否成功；
- unresolved citation / reference；
- missing image / font / linked asset；
- malformed equation / table / figure environment；
- overfull / overflow / clipping 等构建警告（若引擎可报告）；
- 目标 venue 要求的 page size、margin、file type、embedded font 等可机械检查项；
- 生成引擎是否与项目声明的一致。

不能因为最终 PDF “看起来还行”就忽略 build log 中会导致 citation、cross-reference 或 asset 缺失的错误。

### 2.2 Rendered-page correctness

检查实际页面，而不是只看 source：

- 文字是否裁切、重叠、乱码或超出版心；
- Figure / Table 是否变形、过小、被裁掉关键 axis / legend / panel label / scale bar；
- caption 是否与对象分离；
- section heading 是否孤立在页底 / 页顶而对应内容漂到远处；
- 表格是否断裂到难以理解，header 是否按需要重复；
- equation / symbol / superscript / subscript 是否正常显示；
- page break 是否产生异常空白页或大片非意图空白；
- Figure / Table / Supplement / section locator 在渲染后是否仍然正确；
- marked / tracked-change 版本的修改标记是否真实可见；
- anonymous 版本是否在实际页面和文件 metadata 上仍符合当前匿名要求；
- 内容密度和字体是否达到真实阅读场景下的可读性。

页面视觉检查是为了发现工程缺陷，不允许借“美化”重新解释数据或删除科学信息。

## 3. 推荐闭环

正式页面型交付采用：

```text
修改 source
→ 使用目标引擎 build / convert
→ 检查 log / unresolved reference / missing asset
→ 渲染真实交付页
→ 逐页或 contact-sheet 检查
→ 定位具体 defect
→ 最窄必要修改
→ 重新 build / render
→ 直到无 blocking defect
```

最后一次任何会影响分页、Figure 尺寸、citation 数量、section 顺序或 response locator 的修改后，旧渲染验收失效；必须针对新 artifact 重跑。

## 4. 先修根因，不用格式技巧掩盖科学内容

若页面问题来自 Figure 的真实 aspect ratio、表格过宽、caption 太长或内容密度过高，优先从信息组织和源对象解决，不通过扭曲 scientific artifact 来填满页面。

禁止：

- 拉伸 Figure 改变宽高比；
- 裁掉 axis、unit、legend、panel label、scale bar、统计标记或必要注释以“塞进页面”；
- 缩小到实际不可读但技术上不 overflow；
- 用大量手工空格 / 回车 / 不稳定绝对定位伪造布局；
- 为减少页数删除会改变结论的 evidence、limitation 或 provenance；
- 因为某个期刊示例偏好某版式，就把这一偏好当成跨期刊强制标准。

如果 Figure 必须重新生成以适配正式版面，重新执行 [`../FIGURE-WORKFLOW.md`](../FIGURE-WORKFLOW.md) 的 source-data、scientific geometry、annotation 与最终尺寸检查；不能只修改导出尺寸后默认含义未变。

## 5. 不用固定页数或“填满页面”代替可读性

排版目标是完整、稳定、可读且符合当前 venue / institutional rule，而不是机械最小页数或每页视觉占满。

允许合理留白。以下才是问题：

- 空白由 float / layout bug 导致；
- heading 与正文错误分离；
- Figure 被挤到远离第一次引用的位置，造成阅读断裂；
- 一页为了追求“紧凑”导致正文或图表不可读；
- 一个很短的 section 因人工 page break 产生无意义空页。

具体是否允许 landscape、two-column、float-only page、separate figure file 等，按当前 venue 规则处理，不写死 Nature 或其他单一期刊偏好。

## 6. 不静默替换生成引擎或格式

如果项目 / venue 指定了实际编译或转换方式，应优先使用该方式验证最终 artifact。不能因为本机某个工具更方便，就静默用另一个引擎生成看似相近的文件并宣称正式版已通过。

若目标引擎当前不可用：

- 可以做 source-level 检查和可获得的替代预览；
- 明确记录“未在目标引擎完成最终渲染验收”；
- 不能把 substitute rendering 当成目标环境完全兼容的证明。

## 7. Format-specific owner

通用规则之外：

- DOCX 创建 / 修改与逐页验收使用 `general-word-document-generation`；
- PPTX / 学术汇报使用 `scientific-presentation-authoring` 及平台 slides workflow；
- PDF / LaTeX / 其他 page-layout artifact 使用当前可用的 PDF / document / typesetting 工具，并遵守目标 venue 真实模板；
- Figure 自身使用 [`../FIGURE-WORKFLOW.md`](../FIGURE-WORKFLOW.md)。

Communication 只负责确保这些最终 artifact 仍忠于 scientific source 和 submission package，不替代各格式工具。

## 8. 阻断级 defect

以下问题存在时，正式页面型产物不能标记为 ready：

- build 失败或 required artifact 缺失；
- unresolved citation / reference 影响读者定位；
- 关键文字、equation、Figure、Table 被裁切或重叠；
- central scientific evidence 在实际页面不可读；
- Figure 被几何变形或关键科学标注缺失；
- clean / marked / anonymous 版本与声明的内容状态不一致；
- 页面中的 numbering / cross-reference 与最终对象不对应；
- 显示错误改变数字、符号、单位或科学含义；
- 最终渲染结果与最近一次 source 修改不是同一版本。

轻微留白、非关键对齐或不影响理解的视觉偏好可以记录但不必无限迭代。

## 9. 完成条件

Rendered Output QA 完成至少意味着：

1. 使用真实目标格式生成了当前最终 artifact；
2. build / conversion log 中没有未解决的 blocking error；
3. 实际页面已经逐页或通过可靠 overview + 重点页审阅；
4. 关键 Figure / Table / equation / citation / cross-reference 可读且完整；
5. 最后一次影响布局的修改之后重新渲染过；
6. 所有修复仍保持 canonical scientific evidence 与 Claim boundary；
7. 若某个目标环境无法真实验证，限制被显式记录而非假装 PASS。

该 QA 证明“最终页面已按当前环境检查”，不证明不同操作系统、Office/LaTeX 版本或出版商生产系统一定像素级一致；对于这些环境差异只陈述实际验证到的范围。
