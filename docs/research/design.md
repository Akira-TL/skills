# design

`design` 负责把 Research Question 或 Hypothesis 转成可执行的 Research Design，包括 estimand、独立推断单位、sampling、comparison、measurement、controls、missingness、QC、bias protection 和结果前停止规则。

Design 表示“计划做什么”，不是实际发生了什么。进入真实研究实施后，偏离、失败样本和实际 Assay 情况由 `study` 记录，不能为了匹配结果回写已经冻结的 Design。

Akira 的 Git / `research.sqlite` 结果前 freeze 只是项目内部的时间与版本 provenance，不等于外部 preregistration、trial registration、systematic-review protocol registration 或 Registered Report Stage 1 acceptance。对外声称“已预注册 / 已注册”必须有真实 registry / journal artifact、identifier 与登记时序；模板、内部 Design、Git freeze 或“计划注册”都不能当作完成注册的证据。
