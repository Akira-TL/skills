from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_validation import validate
from research_db_ops.candidates import discovery_readiness
from .git import _git
from .language import _canonical_paths, academic_language_readiness
from .literature import literature_completion_readiness
from .project import (
    communication_completion_readiness,
    downstream_completion_readiness,
    planning_completion_readiness,
)

def validate_completion(project_root: Path) -> dict[str, Any]:
    base = validate(project_root)
    errors = list(base["errors"])
    warnings = list(base["warnings"])

    readiness = discovery_readiness(project_root)
    if readiness["has_discovery"] and not readiness["ready_for_saturation"]:
        reasons = ", ".join(
            str(blocker.get("reason", "unknown")) for blocker in readiness["blockers"]
        )
        errors.append(
            "Discovery Candidate 队列尚未闭合，不能作为完成状态或声称 practical conceptual saturation："
            + reasons
        )

    literature = literature_completion_readiness(project_root, readiness)
    for blocker in literature["blockers"]:
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
        elif reason == "database_missing":
            errors.append("research.sqlite 不存在；不能完成 Literature completion gate。")

    downstream = downstream_completion_readiness(project_root)
    for blocker in downstream["blockers"]:
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

    planning = planning_completion_readiness(project_root)
    for blocker in planning["blockers"]:
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
        elif reason == "planning_schema_missing":
            errors.append(
                "Hypothesis/Design provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )

    communication = communication_completion_readiness(project_root)
    for blocker in communication["blockers"]:
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

    academic_language = academic_language_readiness(project_root)
    for blocker in academic_language["blockers"]:
        if blocker.get("reason") == "bare_english_term_in_chinese_communication":
            errors.append(
                f"中文传播稿存在已有成熟中文表述却直接裸用的英文术语：{blocker.get('path')} "
                f"第 {blocker.get('paragraph')} 段（{', '.join(blocker.get('terms', []))}）。"
                "首次出现应优先使用规范的“中文标准术语（English term）”，后续使用中文术语或标准缩写。"
            )
        else:
            errors.append(
                f"中文科研项目的人类可读科研文本存在大段英文叙述：{blocker.get('path')} "
                f"第 {blocker.get('paragraph')} 段。应改为规范中文学术表述；英文仅作为标准术语首次出现时的括注或必要书目信息。"
            )

    git_info: dict[str, Any] = {
        "repository_root": None,
        "head": None,
        "canonical_paths": [],
        "dirty_canonical_paths": [],
    }
    top = _git(project_root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        errors.append("科研项目尚不是 Git repository；不能完成科研 provenance gate。")
    else:
        repo_root = Path(top.stdout.strip()).resolve()
        git_info["repository_root"] = str(repo_root)
        if repo_root != project_root.resolve():
            errors.append(
                f"科研项目根目录不是独立 Git repository top-level：{repo_root}。"
            )

        head = _git(project_root, "rev-parse", "--verify", "HEAD")
        if head.returncode != 0:
            errors.append("科研项目尚无任何 Git commit；研究状态没有形成版本历史。")
        else:
            git_info["head"] = head.stdout.strip()

        canonical_paths = _canonical_paths(project_root)
        git_info["canonical_paths"] = canonical_paths
        for path in canonical_paths:
            tracked = _git(project_root, "ls-files", "--error-unmatch", "--", path)
            if tracked.returncode != 0:
                errors.append(f"canonical research artifact 尚未被 Git 跟踪：{path}")

        if canonical_paths:
            status = _git(
                project_root,
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *canonical_paths,
            )
            dirty = [line for line in status.stdout.splitlines() if line.strip()]
            git_info["dirty_canonical_paths"] = dirty
            if dirty:
                errors.append("canonical research artifacts 仍有未提交修改：" + " | ".join(dirty))

    completion_passed = not errors
    return {
        "ok": completion_passed,
        "completion_checked": True,
        "completion": completion_passed,
        "database": base["database"],
        "errors": errors,
        "warnings": warnings,
        "discovery": readiness,
        "literature": literature,
        "downstream": downstream,
        "planning": planning,
        "communication": communication,
        "academic_language": academic_language,
        "git": git_info,
    }
