from __future__ import annotations

from typing import Any

def append_literature_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "relevant_acquired_not_fully_reviewed":
            errors.append(
                f"相关已获取论文 {blocker.get('paper_id')} 尚未完成 Reconstruction + Critical Audit。"
            )
        elif reason == "targeted_paper_not_fully_reviewed":
            errors.append(
                f"定向直接入库论文 {blocker.get('paper_id')} 处于 active/acquired 状态，但尚未完成 Reconstruction + Critical Audit。"
            )
        elif reason == "core_acquired_not_deep_extraction":
            errors.append(
                f"core + acquired 论文 {blocker.get('paper_id')} 未完成 DEEP_EXTRACTION Reconstruction。"
            )
        elif reason == "acquired_candidate_missing_main_text_access_attempt":
            errors.append(
                f"相关已获取 Candidate {blocker.get('candidate_id')} 缺少可审计的正文获取记录。"
            )
        elif reason == "acquired_paper_missing_main_text_access_attempt":
            errors.append(
                f"定向直接入库论文 {blocker.get('paper_id')} 缺少可审计的正文获取记录。"
            )
        elif reason == "acquired_main_text_access_basis_unverified":
            identity = (
                f"Candidate {blocker.get('candidate_id')}"
                if blocker.get("candidate_id") is not None
                else f"Paper {blocker.get('paper_id')}"
            )
            errors.append(
                f"{identity} 的正文来源依据未核验；来源不明的网络镜像不能闭合为正式全文。"
            )
        elif reason == "acquired_main_text_access_basis_detail_missing":
            identity = (
                f"Candidate {blocker.get('candidate_id')}"
                if blocker.get("candidate_id") is not None
                else f"Paper {blocker.get('paper_id')}"
            )
            errors.append(f"{identity} 的正文获取记录缺少来源依据说明。")
        elif reason == "cross_paper_scientific_relation_missing":
            errors.append(
                "主题型 Literature Discovery 已有多篇完成审阅的论文，但 canonical relation graph "
                "缺少跨论文 scientific relation；SHARES_*/CITES 不能替代 Evidence Synthesis 关系。"
            )
        elif reason == "human_literature_unexpected_top_level":
            errors.append(
                f"literature/ 是固定的人类阅读区，不允许临时新增顶层目录或文件：{blocker.get('path')}。"
                "只使用 literature/to-read/、literature/read/、literature/collections/ 与 literature/README.md。"
            )
        elif reason == "human_literature_non_readable_file":
            errors.append(
                f"人类文献阅读区出现非 Markdown/PDF 文件：{blocker.get('path')}。"
                "XML/HTML、表格、JSON 与其他机器 artifact 应保存在 .research/artifacts/papers/<paper-id>/。"
            )
        elif reason == "human_literature_nested_directory":
            errors.append(
                f"人类文献阅读区应保持平铺的“题名 - 第一作者 - 年份”文件：{blocker.get('path')}。"
            )
        elif reason == "human_literature_pdf_without_note":
            errors.append(
                f"人类阅读区中的 PDF 缺少同名 Markdown 阅读入口：{blocker.get('path')}。"
            )
        elif reason == "human_literature_unregistered_legacy_file":
            errors.append(
                f"legacy literature/papers/ 中存在未登记到 research.sqlite 的游离文件：{blocker.get('path')}。"
            )
        elif reason == "database_missing":
            errors.append("research.sqlite 不存在；不能完成 Literature completion gate。")

def append_downstream_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "tracked_downstream_artifacts_unregistered":
            errors.append(
                "data/analysis 下存在已被 Git 跟踪但未登记到 research.sqlite 的科研 artifact："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "data_assets_present_without_dataset_record":
            errors.append("项目存在 data/ 科研资产，但 research.sqlite 尚未登记 Dataset。")
        elif reason == "analysis_assets_present_without_analysis_record":
            errors.append("项目存在 analysis/ 科研资产，但 research.sqlite 尚未登记 Analysis Run。")
        elif reason == "completed_analysis_missing_dataset_input":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有关联输入 Dataset。")
        elif reason == "completed_analysis_missing_estimate_artifact":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有登记主要 estimate artifact。")
        elif reason == "completed_analysis_missing_project_observation":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有登记项目自身 Observation。")
        elif reason == "analysis_timestamp_invalid":
            errors.append(f"Analysis {blocker.get('analysis')} 的 started_at/completed_at/updated_at 时间戳无效。")
        elif reason == "analysis_completed_before_started":
            errors.append(f"Analysis {blocker.get('analysis')} 的 completed_at 早于 started_at。")
        elif reason == "analysis_completed_after_last_update":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 completed_at 晚于最后一次数据库 updated_at；"
                "完成时间不能指向尚未发生的未来时刻。"
            )
        elif reason == "confirmatory_analysis_missing_freeze_commit":
            errors.append(f"确认性 Analysis {blocker.get('analysis')} 缺少结果可见前 freeze commit。")
        elif reason == "analysis_freeze_commit_missing":
            errors.append(
                f"Analysis {blocker.get('analysis')} 记录的 freeze commit 不存在：{blocker.get('freeze_commit')}。"
            )
        elif reason == "analysis_freeze_commit_not_ancestor":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 freeze commit 不是当前 HEAD 的祖先：{blocker.get('freeze_commit')}。"
            )
        elif reason == "confirmatory_analysis_design_link_missing":
            errors.append(
                f"确认性 Analysis {blocker.get('analysis')} 与已登记 Research Design 匹配，但缺少结构化 design link："
                + ", ".join(str(value) for value in blocker.get("matching_designs", []))
            )
        elif reason == "analysis_design_missing":
            errors.append(
                f"Analysis {blocker.get('analysis')} 引用的 Research Design 不存在：{blocker.get('design_id')}。"
            )
        elif reason == "confirmatory_analysis_design_not_frozen":
            errors.append(
                f"确认性 Analysis {blocker.get('analysis')} 引用的 Research Design {blocker.get('design')} 尚未冻结。"
            )
        elif reason == "design_freeze_after_analysis_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的结果前 freeze 早于 Research Design {blocker.get('design')} 的 freeze；"
                "确认性分析不能先于其设计冻结。"
            )
        elif reason == "analysis_plan_or_input_missing_at_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 freeze commit 未冻结全部主要计划/代码/输入："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "analysis_frozen_artifact_changed_after_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的已冻结计划/代码/输入在 freeze 后发生提交内容变化："
                + ", ".join(str(path) for path in blocker.get("paths", []))
                + "；请保留冻结版本，并把结果后修订作为新增 artifact/amendment。"
            )
        elif reason == "analysis_post_result_context_present_at_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 把 freeze 时已存在的 Dataset artifact 标成 post_result_context："
                + ", ".join(str(path) for path in blocker.get("paths", []))
                + "；post_result_context 只用于结果可见后新增、未参与该执行快照的 provenance/context artifact。"
            )
        elif reason == "analysis_post_result_context_predates_results":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 post_result_context 早于任何已登记 result artifact 进入 Git 历史："
                + ", ".join(str(path) for path in blocker.get("paths", []))
                + "；无法机械证明该 context 是结果可见后才形成的。"
            )
        elif reason == "analysis_result_artifact_present_at_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的结果 artifact 已存在于所声明的 pre-result freeze："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "downstream_schema_missing":
            errors.append(
                "下游科研 provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )

def append_planning_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "hypothesis_artifacts_unregistered":
            errors.append(
                "hypotheses/ 下存在尚未登记到 research.sqlite 的 canonical Hypothesis Set artifact："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "design_artifacts_unregistered":
            errors.append(
                "designs/ 下存在尚未登记到 research.sqlite 的 canonical Research Design artifact："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason in {"hypothesis_freeze_commit_missing", "hypothesis_freeze_commit_not_found"}:
            errors.append(
                f"Hypothesis Set {blocker.get('hypothesis_set')} 缺少有效 freeze commit：{blocker.get('freeze_commit')}。"
            )
        elif reason == "hypothesis_freeze_commit_not_ancestor":
            errors.append(
                f"Hypothesis Set {blocker.get('hypothesis_set')} 的 freeze commit 不是当前 HEAD 的祖先。"
            )
        elif reason == "hypothesis_artifact_missing_at_freeze":
            errors.append(
                f"Hypothesis Set {blocker.get('hypothesis_set')} 的 canonical artifact 在所声明 freeze commit 中不存在："
                f"{blocker.get('path')}"
            )
        elif reason == "hypothesis_set_missing_proposal_provenance":
            errors.append(
                f"Hypothesis Set {blocker.get('hypothesis_set')} 是 schema v18 provenance 启用后新建的集合，"
                "但没有链接任何 Hypothesis Proposal。"
            )
        elif reason in {"design_freeze_commit_missing", "design_freeze_commit_not_found"}:
            errors.append(
                f"Research Design {blocker.get('design')} 缺少有效 freeze commit：{blocker.get('freeze_commit')}。"
            )
        elif reason == "design_freeze_commit_not_ancestor":
            errors.append(
                f"Research Design {blocker.get('design')} 的 freeze commit 不是当前 HEAD 的祖先。"
            )
        elif reason == "design_or_hypothesis_missing_at_freeze":
            errors.append(
                f"Research Design {blocker.get('design')} 的 freeze commit 未同时冻结 Design 与关联 Hypothesis Set："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "linked_hypothesis_missing_freeze":
            errors.append(
                f"Research Design {blocker.get('design')} 已冻结，但关联 Hypothesis Set "
                f"{blocker.get('hypothesis_set')} 没有可审计 freeze commit。"
            )
        elif reason == "hypothesis_freeze_after_design_freeze":
            errors.append(
                f"Research Design {blocker.get('design')} 的 freeze 早于关联 Hypothesis Set "
                f"{blocker.get('hypothesis_set')} 的 freeze；设计不能先于其判别假设冻结。"
            )
        elif reason == "completed_confirmatory_analysis_missing_hypothesis_evaluation":
            errors.append(
                f"确认性 Analysis {blocker.get('analysis')} 已完成并实现 Research Design {blocker.get('design')}，"
                f"但尚未记录对 Hypothesis Set {blocker.get('hypothesis_set')} 的结果后 Evaluation。"
            )
        elif reason == "hypothesis_evaluation_timestamp_invalid":
            errors.append(
                f"Hypothesis Evaluation 的时间戳无效：Analysis {blocker.get('analysis')}，"
                f"Hypothesis Set {blocker.get('hypothesis_set')}。"
            )
        elif reason == "hypothesis_evaluation_before_analysis_completion":
            errors.append(
                f"Hypothesis Evaluation 早于其所引用 Analysis {blocker.get('analysis')} 的 completed_at："
                f"evaluated_at={blocker.get('evaluated_at')}，completed_at={blocker.get('completed_at')}。"
            )
        elif reason == "planning_schema_missing":
            errors.append(
                "Hypothesis/Design provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )

def append_research_tree_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "research_tree_schema_missing":
            errors.append(
                "Research Tree provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )
        elif reason == "research_tree_state_missing":
            errors.append("Research Tree 已存在 Node，但尚未设置 root/active path。")
        elif reason == "research_tree_state_without_nodes":
            errors.append("Research Tree state 已存在，但项目没有任何 Research Node。")
        elif reason in {"research_tree_state_dangling", "research_tree_parent_chain_dangling"}:
            errors.append("Research Tree state 或 parent chain 引用了不存在的 Research Node。")
        elif reason == "research_tree_root_has_parent":
            errors.append(f"Research Tree root {blocker.get('root')} 仍有 parent；root 必须是结构根节点。")
        elif reason == "research_tree_active_node_inactive":
            errors.append(
                f"Research Tree active node {blocker.get('active')} 已处于 {blocker.get('status')}；"
                "active path 必须指向仍可推进的 open/active/blocked 节点。"
            )
        elif reason == "research_tree_parent_cycle":
            errors.append("Research Tree parent chain 出现 cycle。")
        elif reason == "research_tree_active_outside_root":
            errors.append(
                f"Research Tree active node {blocker.get('active')} 不位于 root {blocker.get('root')} 的结构子树中。"
            )


def append_study_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "study_schema_missing":
            errors.append(
                "Study provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )
        elif reason == "study_design_missing":
            errors.append(f"Study {blocker.get('study')} 引用的 Research Design 不存在。")
        elif reason == "study_design_not_frozen":
            errors.append(
                f"Study {blocker.get('study')} 引用的 Research Design {blocker.get('design')} 尚未冻结。"
            )
        elif reason == "study_timestamp_invalid":
            errors.append(f"Study {blocker.get('study')} 的时间戳无效。")
        elif reason == "study_started_after_last_update":
            errors.append(f"Study {blocker.get('study')} 的 started_at 晚于数据库 updated_at。")
        elif reason == "study_completed_before_started":
            errors.append(f"Study {blocker.get('study')} 的 completed_at 早于 started_at。")
        elif reason == "study_completed_after_last_update":
            errors.append(f"Study {blocker.get('study')} 的 completed_at 晚于数据库 updated_at。")
        elif reason == "completed_study_missing_completed_at":
            errors.append(f"已完成 Study {blocker.get('study')} 缺少 completed_at。")
        elif reason == "completed_study_has_active_assays":
            errors.append(
                f"已完成 Study {blocker.get('study')} 仍有未结束 Assay："
                + ", ".join(str(value) for value in blocker.get("assays", []))
            )


def append_communication_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "communication_artifacts_unregistered":
            errors.append(
                "communication/ 下存在未登记到 research.sqlite 的传播 artifact："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "communication_assets_present_without_product_record":
            errors.append("项目存在 communication/ 传播产物，但 research.sqlite 尚未登记 Communication Product。")
        elif reason in {"communication_source_commit_missing", "communication_source_commit_not_found"}:
            errors.append(
                f"Communication Product {blocker.get('communication')} 缺少有效的 pre-communication source commit。"
            )
        elif reason == "communication_source_commit_not_ancestor":
            errors.append(
                f"Communication Product {blocker.get('communication')} 的 source commit 不是当前 HEAD 的祖先。"
            )
        elif reason == "communication_artifact_timing_mismatch":
            errors.append(
                f"Communication Product {blocker.get('communication')} 的 artifact 与 pre-communication source commit 时序不一致："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "scientific_source_changed_after_communication_freeze":
            errors.append(
                f"Communication Product {blocker.get('communication')} 所依据的科研 source commit 之后仍有科学 canonical artifact 变化；"
                "传播稿必须基于最新稳定证据重新审阅："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "completed_communication_missing_artifacts":
            errors.append(f"Communication Product {blocker.get('communication')} 已完成但没有登记传播 artifact。")
        elif reason in {"communication_assets_present_without_database", "communication_schema_missing"}:
            errors.append("Communication provenance schema 尚未迁移完成，但项目已经存在传播产物。")

def append_project_state_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "research_state_missing_file":
            errors.append("项目根目录缺少 RESEARCH.md，不能完成 current research state gate。")
        elif reason == "research_state_missing_sections":
            errors.append(
                "RESEARCH.md 缺少当前科研状态必需 section："
                + ", ".join(str(name) for name in blocker.get("sections", []))
            )
        elif reason == "research_state_invalid_current_loop":
            errors.append(
                "RESEARCH.md 的 Current Loop 不是允许的科研定位词："
                + repr(blocker.get("current_loop"))
            )
        elif reason == "research_state_active_work_empty":
            errors.append(
                "RESEARCH.md 的 Active Work 为空；完成时必须写明下一条真实动作、等待/blocker 或有边界停止状态。"
            )
        elif reason == "research_state_competing_explanation_is_evidence_status":
            errors.append(
                "RESEARCH.md 的 Competing explanations 把证据/工作状态写成了科学竞争解释："
                + ", ".join(str(marker) for marker in blocker.get("markers", []))
                + "。竞争解释必须描述科学对象可能处于的替代状态；证据不足或当前无法判断应写入 Discriminating gap / Current State。"
            )
        elif reason == "research_state_active_work_stale_completion":
            errors.append(
                "RESEARCH.md 的 Active Work 仍描述 Git/validator 收尾动作，说明 current state 尚未在最终提交前刷新："
                + ", ".join(str(marker) for marker in blocker.get("markers", []))
            )


def append_academic_language_errors(errors: list[str], blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        reason = blocker.get("reason")
        if reason in {
            "bare_english_term_in_chinese_communication",
            "bare_english_term_in_chinese_research_text",
        }:
            surface = "中文传播稿" if reason == "bare_english_term_in_chinese_communication" else "中文科研文本"
            errors.append(
                f"{surface}存在已有成熟中文表述却直接裸用的英文术语：{blocker.get('path')} "
                f"第 {blocker.get('paragraph')} 段（{', '.join(blocker.get('terms', []))}）。"
                "首次出现应优先使用规范的“中文标准术语（English term）”，后续使用中文术语或标准缩写。"
            )
        else:
            errors.append(
                f"中文科研项目的人类可读科研文本存在大段英文叙述：{blocker.get('path')} "
                f"第 {blocker.get('paragraph')} 段。应改为规范中文学术表述；英文仅作为标准术语首次出现时的括注或必要书目信息。"
            )
