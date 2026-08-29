from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path
from .git import _git, _git_commit_has_path, _git_first_path_change_after, _git_path_changed_after
from .language import _canonical_paths

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

        for run in connection.execute(
            "SELECT * FROM analysis_runs WHERE status = 'completed' ORDER BY id"
        ):
            analysis_id = int(run["id"])
            slug = str(run["slug"])
            input_rows = connection.execute(
                """
                SELECT d.id, d.slug, d.provenance_path
                FROM analysis_inputs ai
                JOIN datasets d ON d.id = ai.dataset_id
                WHERE ai.analysis_id = ? ORDER BY d.id
                """,
                (analysis_id,),
            ).fetchall()
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

            if run["analysis_mode"] != "confirmatory":
                continue

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
            else:
                design = connection.execute(
                    "SELECT slug, status, freeze_commit FROM research_designs WHERE id = ?",
                    (int(design_id),),
                ).fetchone()
                if design is None:
                    blockers.append(
                        {"reason": "analysis_design_missing", "analysis": slug, "design_id": design_id}
                    )
                elif design["status"] not in {"frozen", "execution_ready"}:
                    blockers.append(
                        {
                            "reason": "confirmatory_analysis_design_not_frozen",
                            "analysis": slug,
                            "design": design["slug"],
                        }
                    )

            freeze_commit = str(run["freeze_commit"] or "").strip()
            if not freeze_commit:
                blockers.append(
                    {"reason": "confirmatory_analysis_missing_freeze_commit", "analysis": slug}
                )
                continue
            commit_exists = _git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}")
            if commit_exists.returncode != 0:
                blockers.append(
                    {
                        "reason": "analysis_freeze_commit_missing",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            ancestor = _git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD")
            if ancestor.returncode != 0:
                blockers.append(
                    {
                        "reason": "analysis_freeze_commit_not_ancestor",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                    }
                )

            if design_id is not None:
                design = connection.execute(
                    "SELECT slug, freeze_commit FROM research_designs WHERE id = ?",
                    (int(design_id),),
                ).fetchone()
                if design is not None:
                    design_freeze = str(design["freeze_commit"] or "").strip()
                    if design_freeze and _git(
                        project_root, "merge-base", "--is-ancestor", design_freeze, freeze_commit
                    ).returncode != 0:
                        blockers.append(
                            {
                                "reason": "design_freeze_after_analysis_freeze",
                                "analysis": slug,
                                "design": design["slug"],
                            }
                        )

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

    return {
        "ready": not blockers,
        "blockers": blockers,
        "dataset_count": dataset_count,
        "analysis_count": analysis_count,
        "completed_analysis_count": completed_analysis_count,
    }


def planning_completion_readiness(project_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "blockers": [{"reason": "database_missing"}],
                "hypothesis_set_count": 0,
                "design_count": 0,
                "frozen_design_count": 0,
                "hypothesis_evaluation_count": 0,
            }

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {"hypothesis_sets", "research_designs", "hypothesis_evaluations"}
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": False,
                "blockers": [{"reason": "planning_schema_missing", "tables": missing}],
                "hypothesis_set_count": 0,
                "design_count": 0,
                "frozen_design_count": 0,
            }

        hypothesis_count = int(connection.execute("SELECT COUNT(*) FROM hypothesis_sets").fetchone()[0])
        design_count = int(connection.execute("SELECT COUNT(*) FROM research_designs").fetchone()[0])
        frozen_design_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM research_designs WHERE status IN ('frozen', 'execution_ready')"
            ).fetchone()[0]
        )
        hypothesis_evaluation_count = int(
            connection.execute("SELECT COUNT(*) FROM hypothesis_evaluations").fetchone()[0]
        )

        registered_hypotheses = {
            str(row["artifact_path"])
            for row in connection.execute("SELECT artifact_path FROM hypothesis_sets ORDER BY id")
        }
        registered_designs = {
            str(row["artifact_path"])
            for row in connection.execute("SELECT artifact_path FROM research_designs ORDER BY id")
        }
        for directory_name, registered, reason in (
            ("hypotheses", registered_hypotheses, "hypothesis_artifacts_unregistered"),
            ("designs", registered_designs, "design_artifacts_unregistered"),
        ):
            directory = project_root / directory_name
            if not directory.exists():
                continue
            actual = {
                path.relative_to(project_root).as_posix()
                for path in directory.rglob("*.md")
                if path.is_file()
            }
            orphaned = sorted(actual - registered)
            if orphaned:
                blockers.append({"reason": reason, "paths": orphaned})

        for hypothesis in connection.execute(
            "SELECT id, slug, artifact_path, status, freeze_commit FROM hypothesis_sets ORDER BY id"
        ):
            if hypothesis["status"] != "frozen":
                continue
            freeze_commit = str(hypothesis["freeze_commit"] or "").strip()
            if not freeze_commit:
                blockers.append(
                    {"reason": "hypothesis_freeze_commit_missing", "hypothesis_set": hypothesis["slug"]}
                )
                continue
            commit_exists = _git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}")
            if commit_exists.returncode != 0:
                blockers.append(
                    {
                        "reason": "hypothesis_freeze_commit_not_found",
                        "hypothesis_set": hypothesis["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            if _git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
                blockers.append(
                    {
                        "reason": "hypothesis_freeze_commit_not_ancestor",
                        "hypothesis_set": hypothesis["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
            if not _git_commit_has_path(project_root, freeze_commit, str(hypothesis["artifact_path"])):
                blockers.append(
                    {
                        "reason": "hypothesis_artifact_missing_at_freeze",
                        "hypothesis_set": hypothesis["slug"],
                        "freeze_commit": freeze_commit,
                        "path": hypothesis["artifact_path"],
                    }
                )

        for design in connection.execute(
            """
            SELECT d.id, d.slug, d.artifact_path, d.status, d.freeze_commit,
                   h.slug AS hypothesis_slug, h.artifact_path AS hypothesis_path,
                   h.freeze_commit AS hypothesis_freeze_commit
            FROM research_designs d
            JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
            WHERE d.status IN ('frozen', 'execution_ready')
            ORDER BY d.id
            """
        ):
            freeze_commit = str(design["freeze_commit"] or "").strip()
            if not freeze_commit:
                blockers.append({"reason": "design_freeze_commit_missing", "design": design["slug"]})
                continue
            if _git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
                blockers.append(
                    {
                        "reason": "design_freeze_commit_not_found",
                        "design": design["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            if _git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
                blockers.append(
                    {
                        "reason": "design_freeze_commit_not_ancestor",
                        "design": design["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
            missing_at_freeze = [
                path
                for path in (str(design["artifact_path"]), str(design["hypothesis_path"]))
                if not _git_commit_has_path(project_root, freeze_commit, path)
            ]
            if missing_at_freeze:
                blockers.append(
                    {
                        "reason": "design_or_hypothesis_missing_at_freeze",
                        "design": design["slug"],
                        "freeze_commit": freeze_commit,
                        "paths": missing_at_freeze,
                    }
                )
            hypothesis_freeze = str(design["hypothesis_freeze_commit"] or "").strip()
            if not hypothesis_freeze:
                blockers.append(
                    {
                        "reason": "linked_hypothesis_missing_freeze",
                        "design": design["slug"],
                        "hypothesis_set": design["hypothesis_slug"],
                    }
                )
            elif _git(
                project_root, "merge-base", "--is-ancestor", hypothesis_freeze, freeze_commit
            ).returncode != 0:
                blockers.append(
                    {
                        "reason": "hypothesis_freeze_after_design_freeze",
                        "design": design["slug"],
                        "hypothesis_set": design["hypothesis_slug"],
                    }
                )

        for run in connection.execute(
            """
            SELECT a.id, a.slug AS analysis_slug, a.design_id,
                   d.slug AS design_slug, d.hypothesis_set_id,
                   h.slug AS hypothesis_slug
            FROM analysis_runs a
            JOIN research_designs d ON d.id = a.design_id
            JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
            WHERE a.analysis_mode = 'confirmatory' AND a.status = 'completed'
            ORDER BY a.id
            """
        ):
            evaluation = connection.execute(
                """
                SELECT id, resolution_status, decision, summary
                FROM hypothesis_evaluations
                WHERE hypothesis_set_id = ? AND analysis_id = ?
                """,
                (int(run["hypothesis_set_id"]), int(run["id"])),
            ).fetchone()
            if evaluation is None:
                blockers.append(
                    {
                        "reason": "completed_confirmatory_analysis_missing_hypothesis_evaluation",
                        "analysis": run["analysis_slug"],
                        "design": run["design_slug"],
                        "hypothesis_set": run["hypothesis_slug"],
                    }
                )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "hypothesis_set_count": hypothesis_count,
        "design_count": design_count,
        "frozen_design_count": frozen_design_count,
        "hypothesis_evaluation_count": hypothesis_evaluation_count,
    }


def communication_completion_readiness(project_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    db_path = database_path(project_root)
    communication_dir = project_root / "communication"
    has_assets = communication_dir.exists() and any(path.is_file() for path in communication_dir.rglob("*"))
    if not db_path.exists():
        return {
            "ready": not has_assets,
            "blockers": ([{"reason": "communication_assets_present_without_database"}] if has_assets else []),
            "product_count": 0,
            "completed_product_count": 0,
        }

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {"communication_products", "communication_artifacts"}
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": not has_assets,
                "blockers": ([{"reason": "communication_schema_missing", "tables": missing}] if has_assets else []),
                "product_count": 0,
                "completed_product_count": 0,
            }

        product_count = int(connection.execute("SELECT COUNT(*) FROM communication_products").fetchone()[0])
        completed_product_count = int(
            connection.execute("SELECT COUNT(*) FROM communication_products WHERE status = 'completed'").fetchone()[0]
        )
        actual_paths = {
            path.relative_to(project_root).as_posix()
            for path in communication_dir.rglob("*")
            if path.is_file()
        } if communication_dir.exists() else set()
        registered_paths = {
            str(row["path"])
            for row in connection.execute("SELECT path FROM communication_artifacts ORDER BY id")
        }
        orphaned = sorted(actual_paths - registered_paths)
        if orphaned:
            blockers.append({"reason": "communication_artifacts_unregistered", "paths": orphaned})
        if has_assets and product_count == 0:
            blockers.append({"reason": "communication_assets_present_without_product_record"})

        scientific_paths = [
            path
            for path in _canonical_paths(project_root)
            if path not in {"RESEARCH.md", ".research/research.sqlite"}
            and not path.startswith("communication/")
        ]
        for product in connection.execute(
            "SELECT * FROM communication_products WHERE status = 'completed' ORDER BY id"
        ):
            product_id = int(product["id"])
            slug = str(product["slug"])
            source_commit = str(product["source_commit"] or "").strip()
            artifacts = connection.execute(
                "SELECT * FROM communication_artifacts WHERE product_id = ? ORDER BY id",
                (product_id,),
            ).fetchall()
            if not artifacts:
                blockers.append({"reason": "completed_communication_missing_artifacts", "communication": slug})
                continue
            if not source_commit:
                blockers.append({"reason": "communication_source_commit_missing", "communication": slug})
                continue
            if _git(project_root, "cat-file", "-e", f"{source_commit}^{{commit}}").returncode != 0:
                blockers.append(
                    {"reason": "communication_source_commit_not_found", "communication": slug, "source_commit": source_commit}
                )
                continue
            if _git(project_root, "merge-base", "--is-ancestor", source_commit, "HEAD").returncode != 0:
                blockers.append(
                    {"reason": "communication_source_commit_not_ancestor", "communication": slug, "source_commit": source_commit}
                )
                continue

            wrong_timing: list[str] = []
            for artifact in artifacts:
                path = str(artifact["path"])
                existed = _git_commit_has_path(project_root, source_commit, path)
                if artifact["timing_role"] == "derived_output" and existed:
                    wrong_timing.append(path)
                if artifact["timing_role"] == "source_support" and not existed:
                    wrong_timing.append(path)
            if wrong_timing:
                blockers.append(
                    {
                        "reason": "communication_artifact_timing_mismatch",
                        "communication": slug,
                        "source_commit": source_commit,
                        "paths": sorted(wrong_timing),
                    }
                )

            changed_science = [
                path
                for path in scientific_paths
                if _git(project_root, "diff", "--quiet", source_commit, "HEAD", "--", path).returncode != 0
            ]
            if changed_science:
                blockers.append(
                    {
                        "reason": "scientific_source_changed_after_communication_freeze",
                        "communication": slug,
                        "source_commit": source_commit,
                        "paths": changed_science,
                    }
                )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "product_count": product_count,
        "completed_product_count": completed_product_count,
    }
