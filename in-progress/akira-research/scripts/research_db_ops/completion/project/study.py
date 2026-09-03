from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect, database_path
from ... import common


def study_completion_readiness(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "checked": True,
            "blockers": [{"reason": "database_missing"}],
            "study_count": 0,
            "completed_study_count": 0,
        }

    blockers: list[dict[str, Any]] = []
    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {
            "studies",
            "study_samples",
            "study_assays",
            "study_assay_samples",
            "study_deviations",
            "study_artifacts",
        }
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": False,
                "checked": True,
                "blockers": [{"reason": "study_schema_missing", "tables": missing}],
                "study_count": 0,
                "completed_study_count": 0,
            }

        study_count = int(connection.execute("SELECT COUNT(*) FROM studies").fetchone()[0])
        completed_study_count = int(
            connection.execute("SELECT COUNT(*) FROM studies WHERE status = 'completed'").fetchone()[0]
        )

        for study in connection.execute(
            """
            SELECT s.id, s.slug, s.status, s.started_at, s.completed_at, s.updated_at,
                   d.slug AS design_slug, d.status AS design_status
            FROM studies s
            LEFT JOIN research_designs d ON d.id = s.design_id
            ORDER BY s.id
            """
        ):
            if study["design_slug"] is None:
                blockers.append(
                    {"reason": "study_design_missing", "study": study["slug"]}
                )
            elif study["design_status"] not in {"frozen", "execution_ready"}:
                blockers.append(
                    {
                        "reason": "study_design_not_frozen",
                        "study": study["slug"],
                        "design": study["design_slug"],
                    }
                )

            try:
                started_at = common.parse_timestamp(study["started_at"], field="Study started_at")
                updated_at = common.parse_timestamp(study["updated_at"], field="Study updated_at")
                completed_at = (
                    common.parse_timestamp(study["completed_at"], field="Study completed_at")
                    if study["completed_at"] is not None
                    else None
                )
            except ResearchDbError:
                blockers.append(
                    {"reason": "study_timestamp_invalid", "study": study["slug"]}
                )
                completed_at = None
                started_at = None
                updated_at = None

            if started_at is not None and updated_at is not None and started_at > updated_at:
                blockers.append(
                    {"reason": "study_started_after_last_update", "study": study["slug"]}
                )
            if completed_at is not None and started_at is not None and completed_at < started_at:
                blockers.append(
                    {"reason": "study_completed_before_started", "study": study["slug"]}
                )
            if completed_at is not None and updated_at is not None and completed_at > updated_at:
                blockers.append(
                    {"reason": "study_completed_after_last_update", "study": study["slug"]}
                )

            if study["status"] == "completed":
                if study["completed_at"] is None:
                    blockers.append(
                        {"reason": "completed_study_missing_completed_at", "study": study["slug"]}
                    )
                active_assays = [
                    str(row["slug"])
                    for row in connection.execute(
                        "SELECT slug FROM study_assays WHERE study_id = ? AND status = 'started' ORDER BY id",
                        (int(study["id"]),),
                    )
                ]
                if active_assays:
                    blockers.append(
                        {
                            "reason": "completed_study_has_active_assays",
                            "study": study["slug"],
                            "assays": active_assays,
                        }
                    )

    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "study_count": study_count,
        "completed_study_count": completed_study_count,
    }
