from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path
from ..git import _git, _git_commit_has_path, _git_first_path_change_after, _git_path_changed_after
from ..language import _canonical_paths

def _append_registration_blockers(
    project_root: Path,
    blockers: list[dict[str, Any]],
    dataset_count: int,
    analysis_count: int,
) -> None:
    tracked = _git(project_root, "ls-files", "--", "data", "analysis")
    tracked_paths = {line.strip() for line in tracked.stdout.splitlines() if line.strip()}
    registered_paths = set(_canonical_paths(project_root))
    orphaned = sorted(tracked_paths - registered_paths)
    if orphaned:
        blockers.append(
            {
                "reason": "tracked_downstream_artifacts_unregistered",
                "paths": orphaned,
            }
        )

    data_dir = project_root / "data"
    if data_dir.exists() and any(path.is_file() for path in data_dir.rglob("*")) and dataset_count == 0:
        blockers.append({"reason": "data_assets_present_without_dataset_record"})
    analysis_dir = project_root / "analysis"
    if analysis_dir.exists() and any(path.is_file() for path in analysis_dir.rglob("*")) and analysis_count == 0:
        blockers.append({"reason": "analysis_assets_present_without_analysis_record"})


def _analysis_input_rows(connection, analysis_id: int):
    return connection.execute(
        """
        SELECT d.id, d.slug, d.provenance_path
        FROM analysis_inputs ai
        JOIN datasets d ON d.id = ai.dataset_id
        WHERE ai.analysis_id = ? ORDER BY d.id
        """,
        (analysis_id,),
    ).fetchall()


def _append_analysis_completeness_blockers(
    connection,
    run,
    blockers: list[dict[str, Any]],
):
    analysis_id = int(run["id"])
    slug = str(run["slug"])
    input_rows = _analysis_input_rows(connection, analysis_id)
    if not input_rows:
        blockers.append(
            {"reason": "completed_analysis_missing_dataset_input", "analysis": slug}
        )
    estimate_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM analysis_artifacts WHERE analysis_id = ? AND role = 'estimate'",
            (analysis_id,),
        ).fetchone()[0]
    )
    if estimate_count == 0:
        blockers.append(
            {"reason": "completed_analysis_missing_estimate_artifact", "analysis": slug}
        )
    observation_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM project_observations WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()[0]
    )
    if observation_count == 0:
        blockers.append(
            {"reason": "completed_analysis_missing_project_observation", "analysis": slug}
        )
    return input_rows


def _append_design_blockers(
    connection,
    run,
    blockers: list[dict[str, Any]],
) -> None:
    slug = str(run["slug"])
    design_id = run["design_id"]
    if design_id is None:
        matching_designs = connection.execute(
            """
            SELECT d.id, d.slug
            FROM research_designs d
            JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
            WHERE d.status <> 'superseded'
              AND (
                trim(d.target_estimand) = trim(?)
                OR trim(h.target_uncertainty) = trim(?)
              )
            ORDER BY d.id
            """,
            (run["estimand"], run["target_uncertainty"]),
        ).fetchall()
        if matching_designs:
            blockers.append(
                {
                    "reason": "confirmatory_analysis_design_link_missing",
                    "analysis": slug,
                    "matching_designs": [str(row["slug"]) for row in matching_designs],
                }
            )
        return

    design = connection.execute(
        "SELECT slug, status, freeze_commit FROM research_designs WHERE id = ?",
        (int(design_id),),
    ).fetchone()
    if design is None:
        blockers.append(
            {"reason": "analysis_design_missing", "analysis": slug, "design_id": design_id}
        )
        return
    if design["status"] not in {"frozen", "execution_ready"}:
        blockers.append(
            {
                "reason": "confirmatory_analysis_design_not_frozen",
                "analysis": slug,
                "design": design["slug"],
            }
        )


def _append_design_freeze_order_blocker(
    project_root: Path,
    connection,
    run,
    blockers: list[dict[str, Any]],
    freeze_commit: str,
) -> None:
    design_id = run["design_id"]
    if design_id is None:
        return
    design = connection.execute(
        "SELECT slug, freeze_commit FROM research_designs WHERE id = ?",
        (int(design_id),),
    ).fetchone()
    if design is None:
        return
    design_freeze = str(design["freeze_commit"] or "").strip()
    if design_freeze and _git(
        project_root, "merge-base", "--is-ancestor", design_freeze, freeze_commit
    ).returncode != 0:
        blockers.append(
            {
                "reason": "design_freeze_after_analysis_freeze",
                "analysis": str(run["slug"]),
                "design": design["slug"],
            }
        )


def _freeze_scope_paths(connection, run, input_rows) -> tuple[list[str], list[str]]:
    analysis_id = int(run["id"])
    freeze_required_paths = [str(run["analysis_path"]), str(run["code_path"])]
    post_result_context_paths: list[str] = []
    freeze_required_paths.extend(
        str(row["path"])
        for row in connection.execute(
            """
            SELECT path FROM analysis_artifacts
            WHERE analysis_id = ? AND timing_role = 'pre_result_support'
            ORDER BY id
            """,
            (analysis_id,),
        )
    )
    for dataset in input_rows:
        freeze_required_paths.append(str(dataset["provenance_path"]))
        for item in connection.execute(
            """
            SELECT da.location, t.timing_role
            FROM dataset_artifacts da
            LEFT JOIN analysis_dataset_artifact_timing t
              ON t.dataset_artifact_id = da.id AND t.analysis_id = ?
            WHERE da.dataset_id = ?
              AND da.storage_kind = 'local'
              AND da.git_tracking = 'required'
            ORDER BY da.id
            """,
            (analysis_id, dataset["id"]),
        ):
            if item["timing_role"] == "post_result_context":
                post_result_context_paths.append(str(item["location"]))
            else:
                freeze_required_paths.append(str(item["location"]))
    return freeze_required_paths, post_result_context_paths


def _append_freeze_snapshot_blockers(
    project_root: Path,
    connection,
    run,
    input_rows,
    blockers: list[dict[str, Any]],
    freeze_commit: str,
) -> None:
    analysis_id = int(run["id"])
    slug = str(run["slug"])
    freeze_required_paths, post_result_context_paths = _freeze_scope_paths(
        connection, run, input_rows
    )
    missing_at_freeze = sorted(
        path
        for path in dict.fromkeys(freeze_required_paths)
        if not _git_commit_has_path(project_root, freeze_commit, path)
    )
    if missing_at_freeze:
        blockers.append(
            {
                "reason": "analysis_plan_or_input_missing_at_freeze",
                "analysis": slug,
                "freeze_commit": freeze_commit,
                "paths": missing_at_freeze,
            }
        )

    changed_after_freeze = sorted(
        path
        for path in dict.fromkeys(freeze_required_paths)
        if _git_commit_has_path(project_root, freeze_commit, path)
        and _git_path_changed_after(project_root, freeze_commit, path)
    )
    if changed_after_freeze:
        blockers.append(
            {
                "reason": "analysis_frozen_artifact_changed_after_freeze",
                "analysis": slug,
                "freeze_commit": freeze_commit,
                "paths": changed_after_freeze,
            }
        )

    result_paths = [
        str(row["path"])
        for row in connection.execute(
            """
            SELECT path FROM analysis_artifacts
            WHERE analysis_id = ? AND timing_role = 'result'
            ORDER BY id
            """,
            (analysis_id,),
        )
    ]
    context_present_at_freeze = sorted(
        path
        for path in dict.fromkeys(post_result_context_paths)
        if _git_commit_has_path(project_root, freeze_commit, path)
    )
    if context_present_at_freeze:
        blockers.append(
            {
                "reason": "analysis_post_result_context_present_at_freeze",
                "analysis": slug,
                "freeze_commit": freeze_commit,
                "paths": context_present_at_freeze,
            }
        )

    premature_context_paths: list[str] = []
    for path in dict.fromkeys(post_result_context_paths):
        if path in context_present_at_freeze:
            continue
        first_context_commit = _git_first_path_change_after(
            project_root, freeze_commit, path
        )
        if first_context_commit is None or not any(
            _git_commit_has_path(project_root, first_context_commit, result_path)
            for result_path in result_paths
        ):
            premature_context_paths.append(path)
    if premature_context_paths:
        blockers.append(
            {
                "reason": "analysis_post_result_context_predates_results",
                "analysis": slug,
                "freeze_commit": freeze_commit,
                "paths": sorted(premature_context_paths),
            }
        )
    result_present_at_freeze = sorted(
        path for path in result_paths if _git_commit_has_path(project_root, freeze_commit, path)
    )
    if result_present_at_freeze:
        blockers.append(
            {
                "reason": "analysis_result_artifact_present_at_freeze",
                "analysis": slug,
                "freeze_commit": freeze_commit,
                "paths": result_present_at_freeze,
            }
        )


def _append_confirmatory_blockers(
    project_root: Path,
    connection,
    run,
    input_rows,
    blockers: list[dict[str, Any]],
) -> None:
    slug = str(run["slug"])
    freeze_commit = str(run["freeze_commit"] or "").strip()

    # Design linkage/frozen-state checks remain before freeze snapshot checks.
    _append_design_blockers(connection, run, blockers)

    if not freeze_commit:
        blockers.append(
            {"reason": "confirmatory_analysis_missing_freeze_commit", "analysis": slug}
        )
        return
    commit_exists = _git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}")
    if commit_exists.returncode != 0:
        blockers.append(
            {
                "reason": "analysis_freeze_commit_missing",
                "analysis": slug,
                "freeze_commit": freeze_commit,
            }
        )
        return
    ancestor = _git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD")
    if ancestor.returncode != 0:
        blockers.append(
            {
                "reason": "analysis_freeze_commit_not_ancestor",
                "analysis": slug,
                "freeze_commit": freeze_commit,
            }
        )

    _append_design_freeze_order_blocker(
        project_root, connection, run, blockers, freeze_commit
    )
    _append_freeze_snapshot_blockers(
        project_root, connection, run, input_rows, blockers, freeze_commit
    )


def downstream_completion_readiness(project_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "blockers": [{"reason": "database_missing"}],
            "dataset_count": 0,
            "analysis_count": 0,
            "completed_analysis_count": 0,
        }

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {
            "datasets",
            "dataset_artifacts",
            "analysis_runs",
            "analysis_inputs",
            "analysis_artifacts",
            "analysis_amendments",
            "project_observations",
        }
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": False,
                "blockers": [{"reason": "downstream_schema_missing", "tables": missing}],
                "dataset_count": 0,
                "analysis_count": 0,
                "completed_analysis_count": 0,
            }

        dataset_count = int(connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
        analysis_count = int(connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0])
        completed_analysis_count = int(
            connection.execute("SELECT COUNT(*) FROM analysis_runs WHERE status = 'completed'").fetchone()[0]
        )
        _append_registration_blockers(project_root, blockers, dataset_count, analysis_count)

        for run in connection.execute(
            "SELECT * FROM analysis_runs WHERE status = 'completed' ORDER BY id"
        ):
            input_rows = _append_analysis_completeness_blockers(connection, run, blockers)
            if run["analysis_mode"] == "confirmatory":
                _append_confirmatory_blockers(
                    project_root, connection, run, input_rows, blockers
                )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "dataset_count": dataset_count,
        "analysis_count": analysis_count,
        "completed_analysis_count": completed_analysis_count,
    }
