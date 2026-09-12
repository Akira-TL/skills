# Data / Code Availability 与投稿数据交付

本文件用于正式论文、综述性数据产物和其他需要 Data Availability / Code Availability / Source Data 的科研传播。它负责把已经存在的 canonical Dataset、Analysis artifact、代码与访问限制准确映射到投稿声明；不负责在 Communication 阶段临时创造数据、改变访问权限或决定科学分析。

## 1. 先盘点真正支撑稿件的全部数据来源

写 Data Availability 前，不从一句模板开始，而是列出当前稿件实际依赖的数据族：

- 本研究新产生的 raw / curated / derived Dataset；
- Figure / Table 的 source data；
- supplementary dataset；
- reused public dataset；
- third-party / licensed dataset；
- controlled-access / sensitive human data；
- simulation / model input；
- manuscript 中 central Claim 依赖但不能公开的其他 data source；
- central code / workflow / trained model（若适用）。

每一项至少映射：

```text
Dataset / artifact identity
→ 支撑哪些 Results / Figure / Table / Claim
→ 当前位置 / repository
→ version / accession / persistent identifier
→ access state
→ licence / use restriction（若适用）
```

“论文里用了数据”与“数据已适合公开交付”不是同一件事。缺失 repository、identifier、README、permission 或 access route 时保持 unresolved，不写成已经可用。

## 2. Repository 与 identifier 按当前领域和 venue 规则选择

选择顺序通常是：

1. 数据类型或期刊有 mandatory repository → 使用其要求的 repository；
2. 无强制要求时，优先领域公认 repository；
3. 无合适领域仓库时，再考虑可靠 generalist / institutional repository；
4. personal website、lab website、临时网盘、未归档 Git repository 或本地路径不能作为正式论文唯一长期访问入口。

具体 repository 名单、强制沉积要求、embargo、reviewer access 和 metadata standard 通过 `research-standards` 查询当前目标期刊 / funder / field；不要把某一家期刊当前规则写成 Akira 永久通用规则。

正式 statement 中只填写**实际已经核验**的 DOI、accession、version、repository、embargo 和 licence。不得根据文件名或计划自行生成 identifier，也不得把“准备上传”写成“available at”。

## 3. Persistent identifier 必须指向正确对象

和文献 DOI 一样，dataset DOI / accession 能解析还不够；至少检查：

- landing page 对应的是目标 dataset；
- title / creators / version 与稿件一致；
- repository record 的 file inventory 与声明一致；
- embargo / private reviewer link 实际可用；
- revised dataset 后稿件引用的是正确 version；
- 一个 identifier 没有把互不相关的多个数据族含混打包而失去可解释性。

临时 share link 可以用于协作，但不冒充长期 persistent identifier。

## 4. 生成数据与复用数据分开声明

不要让读者误以为公开数据库数据是本研究产生的，也不要把本项目新生成的数据藏在一句“data are publicly available”里。

对 reused public data，至少说明实际使用的 dataset / release / accession / version；当 dataset 本身支持主要结论并具有可引用记录时，应按目标 venue 规范正式引用 dataset，而不是只在 Data Availability 中提到数据库主页。

对 mixed data 明确区分：

```text
generated here
reused public
third-party licensed
controlled access
source data / supplementary data
```

## 5. “Available upon request” 不是默认逃生句

如果数据不能公开，statement 至少说明：

```text
为什么受限
谁负责 access decision
什么人 / 什么用途可申请
需要什么 approval / agreement / ethics / legal condition
有哪些 metadata / aggregate / derived data 仍可公开
```

隐私、consent、legal restriction、commercial agreement、third-party ownership 或真实安全限制都可以构成合理理由，但不能只写“因隐私原因不可公开”而不给任何申请路径。

如果只能由 corresponding author 人工转交，也必须确认这是目标 venue 允许且现实可持续的方式；不要把“reasonable request”当默认最佳实践。

第三方数据不能由作者重新授权时，明确 data owner / provider 和合法获取路线；不要替第三方承诺权限。

## 6. Source Data 要和 Figure / Table 对上

对 central quantitative Figure / Table，检查读者是否能从 availability package 定位到支撑它的 source data。至少在适用时提供：

- independent-unit raw / minimally processed values；
- panel / table mapping；
- sample / condition identifiers；
- units 与 missing-value representation；
- exact statistics / test output 或其可重建入口；
- exclusion / filtering notes；
- 从 source data 到 plotting table / Figure 的脚本或明确 producer provenance。

Source Data 不要求把所有机器中间文件全部公开；重点是让稿件中决定性展示能够被核验和重建，同时遵守真实 access / privacy boundary。

## 7. Repository record 至少要让外部研究者知道拿到了什么

长期数据记录按目标标准尽量具备：

- stable title / description；
- creator / contributor；
- persistent identifier；
- version；
- licence / rights 或 access restriction；
- file inventory；
- README / data dictionary；
- variable definition、unit、missing-value code；
- raw / processed / derived 的关系；
- generation / processing provenance；
- manuscript / code / protocol 的 related identifier；
- applicable domain metadata。

FAIR（Findable, Accessible, Interoperable, Reusable）可作为检查框架，但具体必填 metadata、licence 和 repository policy 由领域 / funder / venue 决定，不从通用 checklist 机械推导。

## 8. Code Availability 与 data statement 分工

当软件、分析代码或 workflow 对核心结果重建是必要的，按目标 venue 要求提供 Code Availability 或等价声明。至少区分：

- project source code；
- analysis entrypoint / workflow；
- environment / package versions；
- release / commit used for manuscript；
- archived DOI / release（若适用）；
- third-party / proprietary software restriction；
- credential / controlled system requirement。

代码仓库当前能打开不等于长期可复现。对正式发表版本，优先固定 commit / release；目标 venue、funder 或软件政策要求长期 archive / DOI 时再执行，不强制所有项目使用同一种 archive。

## 9. 禁止编造 availability 信息

Communication 不得编造：

- DOI / accession / repository record；
- data licence；
- embargo date；
- reviewer token / private URL；
- ethics approval 或 consent scope；
- data access committee；
- third-party redistribution permission；
- 已经不存在的 dataset version。

缺少这些信息时保留 placeholder / unresolved，并把下一步精确到“需要 repository deposit / author confirmation / legal or ethics confirmation / access test”，而不是写一个看起来完整但不可核验的 statement。

## 10. Submission 前一致性检查

最终至少检查：

1. 所有支撑 central Claim 的主要 Dataset 都在 availability inventory 中有去向；
2. Data Availability 的 repository / accession / version 与真实记录一致；
3. reused、generated、third-party、restricted data 没有混写；
4. central Figure / Table 的 source data 有可定位映射；
5. restricted data 有具体理由、access route 和条件；
6. manuscript、Supplement、repository landing page、README、Data Availability 与 Code Availability 之间没有版本冲突；
7. private reviewer access 在非作者权限环境下实际测试过（若适用且允许）；
8. revision 后新增 / 删除 Dataset、Figure、Table 或 Analysis 时重新审计 availability statement；
9. target venue / funder 当前的数据与代码政策已经通过 `research-standards` 核验。

Data Availability 只能准确描述已经存在的访问状态；它不能把未完成沉积、未取得许可或未准备 source data 的事实通过措辞变成“可用”。
