from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path
from ..git import _git, _git_commit_has_path, _git_first_path_change_after, _git_path_changed_after
from ..language import _canonical_paths

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
