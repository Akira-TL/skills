# 实验现场记录与原始材料契约

本文件用于把实验现场产生的即时记录、图片、语音转录、仪器截图、手写笔记或其他 contemporaneous material 纳入 Study provenance。目标不是把实验日志做成漂亮笔记，而是保留“当时实际记录了什么”，再从中建立可追溯的结构化 Study 记录。

## 1. 原始记录先保留，再做结构化整理

用户或实验人员提供下列材料时，先把它们视为原始实施证据，而不是可以任意改写的草稿：

- 当日实验文字记录；
- 手写实验本照片；
- 仪器界面 / readout / setup 照片；
- sample / tube / plate / device 标签照片；
- 语音记录或其原始转录；
- 现场导出的仪器 log；
- 临时异常说明、失败说明或操作备注。

结构化 Markdown、Study / Sample / Assay 数据库记录是这些 raw records 的派生解释层。若项目需要长期保存原始材料，应按项目 artifact 规则保存原文件或稳定 pointer，并在派生记录中指回 source；不要只留下 Agent 整理后的文字而丢掉原始上下文。

## 2. 不确定字段不得从上下文补猜

当原始记录没有明确给出温度、时间、浓度、sample ID、instrument setting、operator、batch、replicate identity 或其他可能影响后续推断的字段时：

- 写成 `unknown` / `not recorded` / `awaiting confirmation` 或等价明确状态；
- 记录信息缺口来自哪一份 raw record；
- 如果该字段会改变 Sample identity、protocol interpretation、QC 或 Analysis，向用户 / 实验执行者请求确认；
- 不因为“通常应该是”“上一批大概一样”或图片看起来相似就补写具体值。

后续人工确认时，应作为新的 correction / provenance 记录补上来源和时间；不要静默改写成仿佛最初就已经知道。

## 3. Sample / batch identity 跨记录保持稳定

同一 biological / experimental sample、specimen、batch、plate、run 或 material lot 跨多个实验事件出现时，继续沿用项目中已经建立的稳定 identity。原始记录里的昵称、标签缩写或现场编号可以保留为 alias，但不能因为每次日志写法不同就生成新的 canonical identity。

若两个标签是否代表同一对象尚不确定，保持两个 identity 或 unresolved mapping，等待证据；不要为了整理方便先合并。

## 4. 日志要区分事实、解释和事后补充

实验日志至少区分：

- **当时直接记录的事实**：时间、操作、读数、观察到的异常、文件名等；
- **现场人员当时的解释 / 判断**：例如“可能存在气泡”“怀疑温控异常”；
- **事后整理时新增的解释**：例如根据仪器 log 后来确认温度漂移；
- **事后 correction**：原编号、条件或身份后来被人工纠正。

不能把后来知道的原因回写成“当时已经知道”；也不能把现场人员的猜测升级成 Study fact。

## 5. 异常和失败也是 Study provenance

失败实验、未完成步骤、instrument alarm、污染、漏样、label ambiguity、sample damage、unexpected delay、重复测量或临时 protocol change 不因“这批数据最后没用”就从日志消失。

至少记录：

```text
发生了什么
何时发现
影响哪些 unit / sample / assay
现场采取了什么动作
是否产生 raw output
是否影响后续 QC / exclusion / Analysis
```

是否最终排除数据由后续 Data / Analysis 按预先规则和实际证据决定；Study 日志只忠实记录发生事件。

## 6. 图片和语音是证据来源，不是自动事实提取器

可以从图片或语音中读取标签、显示值、操作信息和异常线索，但：

- 图像模糊、遮挡、反光或缩写不清时保持 unresolved；
- 自动转录可能出错的重要数字 / ID 需要与音频或人工确认；
- 不从未显示的区域推断设置；
- 图像经过 crop、annotation 或增强时保留原图与派生图关系；
- Agent 对图片的解释与图片中直接可见信息分开记录。

## 7. 实验日志不是新的 Design

日志记录 actual execution。若现场发生 deviation：

```text
frozen Design
→ actual execution differs
→ Study records deviation
→ assess impact
→ 必要时返回 Design / Analysis amendment
```

不能因为实际操作改了，就同步修改旧 Design 让它看起来“本来就是这样计划的”。

## 8. 完成条件

把一批现场材料整理成 Study provenance 后至少确认：

1. 原始材料仍可定位；
2. 结构化记录明确指向其 source；
3. 重要缺失字段没有被猜测填充；
4. Sample / batch / assay identity 与项目已有记录一致，或 unresolved mapping 被显式保留；
5. failure / anomaly / deviation 没有因为结果不理想而被删除；
6. 当时事实、当时解释、事后解释和 correction 能够区分；
7. raw output 可以无歧义交给 `data`。
