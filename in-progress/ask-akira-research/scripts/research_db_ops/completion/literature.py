from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path
from research_db_ops.acquisition import (
    acquired_main_text_access_blockers,
    acquired_paper_main_text_access_blockers,
)
from research_db_ops.candidates import discovery_readiness

SCIENTIFIC_RELATION_PREDICATES = {
    "DIRECTLY_SUPPORTS",
    "INDIRECTLY_SUPPORTS",
    "QUALIFIES",
    "CONTRADICTS",
    "DOES_NOT_TEST",
    "LIMITS",
    "CHALLENGES",
    "WEAKENS",
}
RELATION_ENTITY_TABLES = {
    "method": "methods",
    "experiment": "experiments",
    "observation": "observations",
    "claim": "claims",
    "issue": "issues",
    "lead": "leads",
}


def _entity_paper_id(connection, entity_type: str, entity_id: str) -> str | None:
    if entity_type == "paper":
        row = connection.execute("SELECT id FROM papers WHERE id = ?", (entity_id,)).fetchone()
        return str(row["id"]) if row else None
    table = RELATION_ENTITY_TABLES.get(entity_type)
    if table is None:
        return None
    row = connection.execute(
        f'SELECT paper_id FROM "{table}" WHERE CAST(id AS TEXT) = ?', (entity_id,)
    ).fetchone()
    return str(row["paper_id"]) if row else None


def literature_completion_readiness(
    project_root: Path, discovery: dict[str, Any] | None = None
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    core_acquired_count = 0
    relevant_acquired_count = 0
    critically_reviewed_count = 0
    cross_paper_scientific_relations: list[int] = []
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "blockers": [{"reason": "database_missing"}],
            "core_acquired_count": 0,
            "relevant_acquired_count": 0,
            "critically_reviewed_count": 0,
            "cross_paper_scientific_relation_count": 0,
        }

    with connect(db_path) as connection:
        acquired = connection.execute(
            """
            SELECT c.id AS candidate_id, c.title, c.reading_priority, c.paper_id,
                   p.read_depth, p.reading_status, p.critical_status
            FROM candidates c
            LEFT JOIN papers p ON p.id = c.paper_id
            WHERE c.relevance_status = 'relevant'
              AND c.acquisition_status = 'acquired'
            ORDER BY c.id
            """
        ).fetchall()
        relevant_acquired_count = len(acquired)
        for row in acquired:
            paper_id = row["paper_id"]
            if not paper_id:
                continue
            blockers.extend(acquired_main_text_access_blockers(connection, int(row["candidate_id"])))
            if row["reading_status"] != "extracted" or row["critical_status"] != "critically_reviewed":
                blockers.append(
                    {
                        "reason": "relevant_acquired_not_fully_reviewed",
                        "candidate_id": int(row["candidate_id"]),
                        "paper_id": paper_id,
                        "title": row["title"],
                    }
                )
            else:
                critically_reviewed_count += 1
            if row["reading_priority"] == "core":
                core_acquired_count += 1
                deep_run = connection.execute(
                    """
                    SELECT 1 FROM reading_runs
                    WHERE paper_id = ? AND pass = 'reconstruction'
                      AND depth = 'deep_extraction' AND completed_at IS NOT NULL
                    LIMIT 1
                    """,
                    (paper_id,),
                ).fetchone()
                if row["read_depth"] != "deep_extraction" or deep_run is None:
                    blockers.append(
                        {
                            "reason": "core_acquired_not_deep_extraction",
                            "candidate_id": int(row["candidate_id"]),
                            "paper_id": paper_id,
                            "title": row["title"],
                            "read_depth": row["read_depth"],
                            "deep_reconstruction_run": deep_run is not None,
                        }
                    )

        targeted_papers = connection.execute(
            """
            SELECT p.id, p.title, p.status, p.reading_status, p.critical_status
            FROM papers p
            WHERE p.status IN ('acquired', 'active')
              AND NOT EXISTS (SELECT 1 FROM candidates c WHERE c.paper_id = p.id)
            ORDER BY p.id
            """
        ).fetchall()
        for paper in targeted_papers:
            paper_id = str(paper["id"])
            blockers.extend(acquired_paper_main_text_access_blockers(connection, paper_id))
            if paper["reading_status"] != "extracted" or paper["critical_status"] != "critically_reviewed":
                blockers.append(
                    {
                        "reason": "targeted_paper_not_fully_reviewed",
                        "paper_id": paper_id,
                        "title": paper["title"],
                    }
                )
            else:
                critically_reviewed_count += 1

        for relation in connection.execute(
            """
            SELECT id, subject_type, subject_id, predicate, object_type, object_id
            FROM relations ORDER BY id
            """
        ):
            if relation["predicate"] not in SCIENTIFIC_RELATION_PREDICATES:
                continue
            subject_paper = _entity_paper_id(
                connection, str(relation["subject_type"]), str(relation["subject_id"])
            )
            object_paper = _entity_paper_id(
                connection, str(relation["object_type"]), str(relation["object_id"])
            )
            if subject_paper and object_paper and subject_paper != object_paper:
                cross_paper_scientific_relations.append(int(relation["id"]))

    discovery = discovery or discovery_readiness(project_root)
    topical_discovery = (
        int(discovery.get("relevant_candidate_count", 0)) >= 2
        and bool(set(discovery.get("discovery_families", [])) & {"query_search", "related_work"})
    )
    if topical_discovery and critically_reviewed_count >= 2 and not cross_paper_scientific_relations:
        blockers.append(
            {
                "reason": "cross_paper_scientific_relation_missing",
                "reviewed_paper_count": critically_reviewed_count,
            }
        )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "core_acquired_count": core_acquired_count,
        "relevant_acquired_count": relevant_acquired_count,
        "critically_reviewed_count": critically_reviewed_count,
        "cross_paper_scientific_relation_count": len(cross_paper_scientific_relations),
        "cross_paper_scientific_relation_ids": cross_paper_scientific_relations,
    }
