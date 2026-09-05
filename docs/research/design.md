# design

`design` 负责把 Research Question 或 Hypothesis 转成可执行的 Research Design，包括 estimand、独立推断单位、sampling、comparison、measurement、controls、missingness、QC、bias protection 和结果前停止规则。

Design 表示“计划做什么”，不是实际发生了什么。进入真实研究实施后，偏离、失败样本和实际 Assay 情况由 `study` 记录，不能为了匹配结果回写已经冻结的 Design。
