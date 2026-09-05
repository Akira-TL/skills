from __future__ import annotations

from pathlib import Path

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError

def _check_downstream_project(project_root: Path, connection, errors: list[str]) -> None:
    for row in connection.execute(
        "SELECT id, slug, provenance_path FROM datasets ORDER BY id"
    ):
        path = Path(str(row["provenance_path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.exists():
            errors.append(
                f"dataset {row['slug']} 的 provenance_path 文件不存在：{path}"
            )

    for row in connection.execute(
        "SELECT id, dataset_id, location, storage_kind FROM dataset_artifacts ORDER BY id"
    ):
        if row["storage_kind"] != "local":
            continue
        path = Path(str(row["location"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.exists():
            errors.append(f"dataset artifact {row['id']} 文件不存在：{path}")

    for row in connection.execute(
        """
        SELECT t.analysis_id, a.slug AS analysis_slug, da.id AS dataset_artifact_id,
               da.location, da.storage_kind, da.git_tracking
        FROM analysis_dataset_artifact_timing t
        JOIN analysis_runs a ON a.id = t.analysis_id
        JOIN dataset_artifacts da ON da.id = t.dataset_artifact_id
        LEFT JOIN analysis_inputs ai
          ON ai.analysis_id = t.analysis_id AND ai.dataset_id = da.dataset_id
        WHERE ai.analysis_id IS NULL
           OR da.storage_kind <> 'local'
           OR da.git_tracking <> 'required'
        ORDER BY t.analysis_id, da.id
        """
    ):
        if row["storage_kind"] != "local" or row["git_tracking"] != "required":
            errors.append(
                "analysis dataset artifact timing 只能引用 local + git_tracking=required "
                f"的 canonical artifact：analysis={row['analysis_slug']}; "
                f"artifact={row['location']}"
            )
        else:
            errors.append(
                "analysis dataset artifact timing 引用了未连接到当前 Analysis 的 Dataset artifact："
                f"analysis={row['analysis_slug']}; artifact={row['location']}"
            )

    for row in connection.execute(
        """
        SELECT a.id, a.slug, a.analysis_path, a.code_path, a.analysis_mode,
               a.status, a.freeze_commit, a.design_id, a.estimand,
               d.id AS design_exists, d.target_estimand AS design_estimand
        FROM analysis_runs a
        LEFT JOIN research_designs d ON d.id = a.design_id
        ORDER BY a.id
        """
    ):
        for field in ("analysis_path", "code_path"):
            path = Path(str(row[field]))
            if not path.is_absolute():
                path = project_root / path
            if not path.exists():
                errors.append(
                    f"analysis {row['slug']} 的 {field} 文件不存在：{path}"
                )
        if (
            row["analysis_mode"] == "confirmatory"
            and row["status"] in {"frozen", "completed"}
            and not (row["freeze_commit"] and str(row["freeze_commit"]).strip())
        ):
            errors.append(
                f"confirmatory analysis {row['slug']} 已进入 {row['status']}，但缺少 freeze_commit。"
            )
        if row["design_id"] is not None:
            if row["design_exists"] is None:
                errors.append(f"analysis {row['slug']} 引用不存在的 Research Design。")
            elif str(row["estimand"]).strip() != str(row["design_estimand"]).strip():
                errors.append(
                    f"analysis {row['slug']} 的 estimand 与关联 Research Design 不一致。"
                )

    for row in connection.execute(
        "SELECT id, analysis_id, path FROM analysis_artifacts ORDER BY id"
    ):
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.exists():
            errors.append(f"analysis artifact {row['id']} 文件不存在：{path}")

    for row in connection.execute(
        """
        SELECT o.id, o.analysis_id, a.analysis_id AS artifact_analysis_id
        FROM project_observations o
        LEFT JOIN analysis_artifacts a ON a.id = o.source_artifact_id
        WHERE o.source_artifact_id IS NOT NULL
        ORDER BY o.id
        """
    ):
        if row["artifact_analysis_id"] != row["analysis_id"]:
            errors.append(
                f"project observation {row['id']} 的 source artifact 不属于同一 Analysis。"
            )


def _check_planning_project(project_root: Path, connection, errors: list[str]) -> None:
    tables = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    proposal_schema = {
        "hypothesis_proposals",
        "hypothesis_set_proposals",
        "user_hypothesis_decisions",
        "research_judgments",
    }.issubset(tables)
    provenance_row = connection.execute(
        "SELECT value FROM meta WHERE key = 'hypothesis_provenance_started_at'"
    ).fetchone()
    provenance_started_at = str(provenance_row["value"]) if provenance_row is not None else None

    for row in connection.execute(
        "SELECT id, slug, artifact_path, status, freeze_commit, created_at FROM hypothesis_sets ORDER BY id"
    ):
        path = Path(str(row["artifact_path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            errors.append(
                f"hypothesis set {row['slug']} 的 artifact_path 文件不存在：{path}"
            )
        if row["status"] == "frozen" and not (
            row["freeze_commit"] and str(row["freeze_commit"]).strip()
        ):
            errors.append(
                f"hypothesis set {row['slug']} 已 frozen，但缺少 freeze_commit。"
            )
        if proposal_schema and provenance_started_at:
            is_post_v18 = connection.execute(
                "SELECT julianday(?) >= julianday(?)",
                (row["created_at"], provenance_started_at),
            ).fetchone()[0]
            if is_post_v18:
                proposal_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM hypothesis_set_proposals WHERE hypothesis_set_id = ?",
                        (int(row["id"]),),
                    ).fetchone()[0]
                )
                if proposal_count == 0:
                    errors.append(
                        f"hypothesis set {row['slug']} 是 proposal provenance 启用后新建的集合，"
                        "但没有链接任何 Hypothesis Proposal。"
                    )

    if proposal_schema:
        for row in connection.execute(
            """
            SELECT hp.hypothesis_set_id, hp.proposal_id,
                   h.id AS hypothesis_exists, p.id AS proposal_exists
            FROM hypothesis_set_proposals hp
            LEFT JOIN hypothesis_sets h ON h.id = hp.hypothesis_set_id
            LEFT JOIN hypothesis_proposals p ON p.id = hp.proposal_id
            ORDER BY hp.hypothesis_set_id, hp.proposal_id
            """
        ):
            if row["hypothesis_exists"] is None or row["proposal_exists"] is None:
                errors.append(
                    "hypothesis_set_proposals 存在悬空 provenance link："
                    f"hypothesis_set_id={row['hypothesis_set_id']}; proposal_id={row['proposal_id']}"
                )
        for row in connection.execute(
            """
            SELECT d.id, d.proposal_id, d.resulting_proposal_id,
                   p.id AS proposal_exists, rp.id AS resulting_exists
            FROM user_hypothesis_decisions d
            LEFT JOIN hypothesis_proposals p ON p.id = d.proposal_id
            LEFT JOIN hypothesis_proposals rp ON rp.id = d.resulting_proposal_id
            ORDER BY d.id
            """
        ):
            if row["proposal_exists"] is None:
                errors.append(f"user hypothesis decision {row['id']} 引用不存在的 proposal。")
            if row["resulting_proposal_id"] is not None and row["resulting_exists"] is None:
                errors.append(
                    f"user hypothesis decision {row['id']} 的 resulting proposal 不存在。"
                )

    for row in connection.execute(
        """
        SELECT d.id, d.slug, d.artifact_path, d.status, d.feasibility_status,
               d.feasibility_summary, d.freeze_commit, d.hypothesis_set_id,
               d.question_node_id, h.id AS hypothesis_id,
               q.id AS question_id, q.kind AS question_kind
        FROM research_designs d
        LEFT JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
        LEFT JOIN research_nodes q ON q.id = d.question_node_id
        ORDER BY d.id
        """
    ):
        path = Path(str(row["artifact_path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            errors.append(f"research design {row['slug']} 的 artifact_path 文件不存在：{path}")
        if row["hypothesis_set_id"] is None and row["question_node_id"] is None:
            errors.append(
                f"research design {row['slug']} 没有链接 Research Question 或 Hypothesis Set。"
            )
        if row["hypothesis_set_id"] is not None and row["hypothesis_id"] is None:
            errors.append(f"research design {row['slug']} 引用不存在的 Hypothesis Set。")
        if row["question_node_id"] is not None:
            if row["question_id"] is None:
                errors.append(f"research design {row['slug']} 引用不存在的 Research Question Node。")
            elif row["question_kind"] != "question":
                errors.append(f"research design {row['slug']} 的 question_node_id 不是 question Node。")
        if row["status"] in {"frozen", "execution_ready"} and not (
            row["freeze_commit"] and str(row["freeze_commit"]).strip()
        ):
            errors.append(
                f"research design {row['slug']} 已进入 {row['status']}，但缺少 freeze_commit。"
            )
        if row["feasibility_status"] == "unresolved" and not (
            row["feasibility_summary"] and str(row["feasibility_summary"]).strip()
        ):
            errors.append(
                f"research design {row['slug']} feasibility_status=unresolved，但缺少 feasibility_summary。"
            )
        if row["status"] == "execution_ready" and row["feasibility_status"] != "ready":
            errors.append(
                f"research design {row['slug']} 标记 execution_ready，但 feasibility_status 不是 ready。"
            )

    for row in connection.execute(
        """
        SELECT e.id, e.hypothesis_set_id, e.analysis_id, e.source_artifact_id,
               e.decision, e.summary, a.status AS analysis_status, a.design_id,
               d.hypothesis_set_id AS design_hypothesis_set_id,
               aa.analysis_id AS source_artifact_analysis_id
        FROM hypothesis_evaluations e
        LEFT JOIN analysis_runs a ON a.id = e.analysis_id
        LEFT JOIN research_designs d ON d.id = a.design_id
        LEFT JOIN analysis_artifacts aa ON aa.id = e.source_artifact_id
        ORDER BY e.id
        """
    ):
        if row["analysis_status"] != "completed":
            errors.append(
                f"hypothesis evaluation {row['id']} 必须引用 completed Analysis。"
            )
        if row["design_id"] is not None and row["design_hypothesis_set_id"] != row["hypothesis_set_id"]:
            errors.append(
                f"hypothesis evaluation {row['id']} 与 Analysis 所实现 Design 的 Hypothesis Set 不一致。"
            )
        if row["source_artifact_analysis_id"] != row["analysis_id"]:
            errors.append(
                f"hypothesis evaluation {row['id']} 的 source artifact 不属于同一 Analysis。"
            )
        if not (row["decision"] and str(row["decision"]).strip()):
            errors.append(f"hypothesis evaluation {row['id']} 缺少 decision。")
        if not (row["summary"] and str(row["summary"]).strip()):
            errors.append(f"hypothesis evaluation {row['id']} 缺少 summary。")


def _check_research_tree_project(project_root: Path, connection, errors: list[str]) -> None:
    nodes = {
        int(row["id"]): row
        for row in connection.execute(
            "SELECT id, slug, parent_node_id, artifact_path FROM research_nodes ORDER BY id"
        )
    }
    for row in nodes.values():
        if row["artifact_path"]:
            path = Path(str(row["artifact_path"]))
            if not path.is_absolute():
                path = project_root / path
            if not path.is_file():
                errors.append(f"research node {row['slug']} 的 artifact_path 文件不存在：{path}")

        seen: set[int] = set()
        current_id: int | None = int(row["id"])
        while current_id is not None:
            if current_id in seen:
                errors.append(f"research node {row['slug']} 的 parent chain 出现 cycle。")
                break
            seen.add(current_id)
            current = nodes.get(current_id)
            if current is None:
                errors.append(f"research node {row['slug']} 的 parent chain 引用不存在的 Node。")
                break
            current_id = (
                int(current["parent_node_id"])
                if current["parent_node_id"] is not None
                else None
            )

    state = connection.execute(
        "SELECT root_node_id, active_node_id FROM research_tree_state WHERE id = 1"
    ).fetchone()
    if state is not None:
        root = nodes.get(int(state["root_node_id"]))
        active = nodes.get(int(state["active_node_id"]))
        if root is None or active is None:
            errors.append("research tree state 引用了不存在的 Node。")
        else:
            if root["parent_node_id"] is not None:
                errors.append(f"research tree root {root['slug']} 不能有 parent。")
            seen: set[int] = set()
            current_id: int | None = int(active["id"])
            reached_root = False
            while current_id is not None:
                if current_id in seen:
                    break
                seen.add(current_id)
                if current_id == int(root["id"]):
                    reached_root = True
                    break
                current = nodes.get(current_id)
                if current is None:
                    break
                current_id = (
                    int(current["parent_node_id"])
                    if current["parent_node_id"] is not None
                    else None
                )
            if not reached_root:
                errors.append(
                    f"research tree active node {active['slug']} 不位于 root {root['slug']} 的结构子树中。"
                )


def _check_study_project(project_root: Path, connection, errors: list[str]) -> None:
    for row in connection.execute(
        """
        SELECT s.id, s.slug, s.status, s.provenance_path, s.started_at,
               s.completed_at, s.updated_at, d.id AS design_exists,
               d.status AS design_status
        FROM studies s
        LEFT JOIN research_designs d ON d.id = s.design_id
        ORDER BY s.id
        """
    ):
        path = Path(str(row["provenance_path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            errors.append(f"study {row['slug']} 的 provenance_path 文件不存在：{path}")
        if row["design_exists"] is None:
            errors.append(f"study {row['slug']} 引用不存在的 Research Design。")
        elif row["design_status"] not in {"frozen", "execution_ready"}:
            errors.append(f"study {row['slug']} 引用的 Research Design 尚未冻结。")
        try:
            started_at = common.parse_timestamp(row["started_at"], field="Study started_at")
            updated_at = common.parse_timestamp(row["updated_at"], field="Study updated_at")
            completed_at = (
                common.parse_timestamp(row["completed_at"], field="Study completed_at")
                if row["completed_at"] is not None
                else None
            )
        except ResearchDbError:
            errors.append(f"study {row['slug']} 的时间戳无效。")
        else:
            if started_at > updated_at:
                errors.append(f"study {row['slug']} 的 started_at 晚于 updated_at。")
            if completed_at is not None and completed_at < started_at:
                errors.append(f"study {row['slug']} 的 completed_at 早于 started_at。")
            if completed_at is not None and completed_at > updated_at:
                errors.append(f"study {row['slug']} 的 completed_at 晚于 updated_at。")
        if row["status"] == "completed" and row["completed_at"] is None:
            errors.append(f"completed study {row['slug']} 缺少 completed_at。")

    for row in connection.execute(
        "SELECT id, study_id, parent_sample_id FROM study_samples WHERE parent_sample_id IS NOT NULL"
    ):
        parent = connection.execute(
            "SELECT study_id FROM study_samples WHERE id = ?", (int(row["parent_sample_id"]),)
        ).fetchone()
        if parent is None or int(parent["study_id"]) != int(row["study_id"]):
            errors.append(f"study sample {row['id']} 的 parent sample 不属于同一 Study。")

    for row in connection.execute(
        """
        SELECT x.assay_id, x.sample_id, a.study_id AS assay_study_id,
               s.study_id AS sample_study_id
        FROM study_assay_samples x
        LEFT JOIN study_assays a ON a.id = x.assay_id
        LEFT JOIN study_samples s ON s.id = x.sample_id
        ORDER BY x.assay_id, x.sample_id
        """
    ):
        if (
            row["assay_study_id"] is None
            or row["sample_study_id"] is None
            or int(row["assay_study_id"]) != int(row["sample_study_id"])
        ):
            errors.append(
                f"study assay/sample link 跨越了不同 Study：assay={row['assay_id']}; sample={row['sample_id']}"
            )

    for row in connection.execute(
        "SELECT id, location, storage_kind FROM study_artifacts ORDER BY id"
    ):
        if row["storage_kind"] != "local":
            continue
        path = Path(str(row["location"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.exists():
            errors.append(f"study artifact {row['id']} 文件不存在：{path}")


def _check_communication_project(project_root: Path, connection, errors: list[str]) -> None:
    for row in connection.execute(
        """
        SELECT a.id, a.product_id, a.path, p.id AS product_exists
        FROM communication_artifacts a
        LEFT JOIN communication_products p ON p.id = a.product_id
        ORDER BY a.id
        """
    ):
        if row["product_exists"] is None:
            errors.append(f"communication artifact {row['id']} 引用不存在的 Communication Product。")
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            errors.append(f"communication artifact {row['id']} 文件不存在：{path}")

def check_project(project_root: Path, connection, errors: list[str]) -> None:
    _check_downstream_project(project_root, connection, errors)
    _check_planning_project(project_root, connection, errors)
    _check_research_tree_project(project_root, connection, errors)
    _check_study_project(project_root, connection, errors)
    _check_communication_project(project_root, connection, errors)
