from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path
from ..git import run_git, commit_has_path, first_path_change_after, path_changed_after
from ..language import canonical_paths

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
            commit_exists = run_git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}")
            if commit_exists.returncode != 0:
                blockers.append(
                    {
                        "reason": "hypothesis_freeze_commit_not_found",
                        "hypothesis_set": hypothesis["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            if run_git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
                blockers.append(
                    {
                        "reason": "hypothesis_freeze_commit_not_ancestor",
                        "hypothesis_set": hypothesis["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
            if not commit_has_path(project_root, freeze_commit, str(hypothesis["artifact_path"])):
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
            if run_git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}").returncode != 0:
                blockers.append(
                    {
                        "reason": "design_freeze_commit_not_found",
                        "design": design["slug"],
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            if run_git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
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
                if not commit_has_path(project_root, freeze_commit, path)
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
            elif run_git(
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
