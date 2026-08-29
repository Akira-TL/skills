from __future__ import annotations

from pathlib import Path


def check_project(project_root: Path, connection, errors: list[str]) -> None:
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

    for row in connection.execute(
        "SELECT id, slug, artifact_path, status, freeze_commit FROM hypothesis_sets ORDER BY id"
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

    for row in connection.execute(
        """
        SELECT d.id, d.slug, d.artifact_path, d.status, d.feasibility_status,
               d.feasibility_summary, d.freeze_commit, h.id AS hypothesis_id
        FROM research_designs d
        LEFT JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
        ORDER BY d.id
        """
    ):
        path = Path(str(row["artifact_path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            errors.append(f"research design {row['slug']} 的 artifact_path 文件不存在：{path}")
        if row["hypothesis_id"] is None:
            errors.append(f"research design {row['slug']} 引用不存在的 Hypothesis Set。")
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
