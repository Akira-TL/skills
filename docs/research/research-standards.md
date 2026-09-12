# research-standards

`research-standards` 用于核验当前研究真正适用的既有科研规范、指南和方法学来源，并区分研究设计指导、报告规范、metadata 标准、provenance 标准、数据管理原则、方法学依据和软件文档的不同职责。

它不会把 ARRIVE、CONSORT、STROBE 等报告规范当成因果识别或统计设计方法。通常由 `akira-research` 或其他科研子 Skill 在规范会影响当前动作时自动调用。

涉及伦理审查、人类受试者、个人/敏感数据、临床研究、动物研究、许可或跨境数据/材料时，`research-standards` 会把“当前权威来源是什么”和“它是否适用于本项目”分开处理。适用性缺少关键事实时保持 unresolved，不能把 unknown 写成 not applicable，也不能从对话语言、用户 locale、作者 affiliation 或 manuscript wording 推断 jurisdiction、approval、waiver、consent。多个 institution / jurisdiction / funder authority 冲突时并列保留，并交给有权机构或人员决定；Akira 不把规范整理结果包装成 IRB/REC 决定、法律意见或 institutional authorization。
