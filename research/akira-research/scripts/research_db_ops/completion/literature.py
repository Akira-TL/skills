from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.schema import KNOWLEDGE_ENTITY_TABLES
from research_db_support.storage import connect, database_path
from research_db_ops.acquisition import (
    acquired_main_text_access_blockers,
    acquired_paper_main_text_access_blockers,
)
from research_db_ops.candidates import discovery_readiness
from research_db_ops.user_reading import parse_confirmation_controls
from research_db_support.storage import ResearchDbError

HUMAN_LITERATURE_DIRS = {"papers", "collections"}
HUMAN_READING_SUFFIXES = {".md", ".pdf"}


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


def _legacy_registered_literature_paths(project_root: Path) -> set[str]:
    db_path = database_path(project_root)
    if not db_path.exists():
        return set()
    registered: set[str] = set()
    with connect(db_path) as connection:
        for row in connection.execute("SELECT path FROM artifacts ORDER BY id"):
            path = Path(str(row["path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            value = path.as_posix()
            if value.startswith("literature/papers/"):
                registered.add(value)
        for row in connection.execute(
            "SELECT sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
        ):
            path = Path(str(row["sidecar_path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            value = path.as_posix()
            if value.startswith("literature/papers/"):
                registered.add(value)
    return registered


def literature_human_view_readiness(project_root: Path) -> dict[str, Any]:
    root = project_root / "literature"
    if not root.exists():
        return {"ready": True, "blockers": [], "legacy_paths": []}

    blockers: list[dict[str, Any]] = []
    legacy_paths: list[str] = []
    legacy_registered = _legacy_registered_literature_paths(project_root)

    for child in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
        relative = child.relative_to(project_root).as_posix()
        if child.name == "README.md" and child.is_file():
            continue
        if child.name not in HUMAN_LITERATURE_DIRS or not child.is_dir():
            blockers.append(
                {
                    "reason": "human_literature_unexpected_top_level",
                    "path": relative,
                }
            )
            continue

        if child.name == "collections":
            for entry in sorted(child.iterdir(), key=lambda path: path.name.casefold()):
                entry_relative = entry.relative_to(project_root).as_posix()
                if entry.is_dir():
                    blockers.append({"reason": "human_literature_nested_directory", "path": entry_relative})
                elif not entry.is_file() or entry.suffix.casefold() != ".md":
                    blockers.append({"reason": "human_literature_non_readable_file", "path": entry_relative})
            continue

        stems_with_notes: set[str] = set()
        pdf_paths: list[Path] = []
        for entry in sorted(child.iterdir(), key=lambda path: path.name.casefold()):
            entry_relative = entry.relative_to(project_root).as_posix()
            if entry.is_dir():
                legacy_files = sorted(path for path in entry.rglob("*") if path.is_file())
                if not legacy_files:
                    blockers.append({"reason": "human_literature_nested_directory", "path": entry_relative})
                    continue
                for legacy_file in legacy_files:
                    legacy_relative = legacy_file.relative_to(project_root).as_posix()
                    if legacy_relative in legacy_registered:
                        legacy_paths.append(legacy_relative)
                    else:
                        blockers.append(
                            {
                                "reason": "human_literature_unregistered_legacy_file",
                                "path": legacy_relative,
                            }
                        )
                continue
            if not entry.is_file() or entry.suffix.casefold() not in HUMAN_READING_SUFFIXES:
                blockers.append({"reason": "human_literature_non_readable_file", "path": entry_relative})
                continue
            if entry.suffix.casefold() == ".md":
                stems_with_notes.add(entry.stem)
                try:
                    parse_confirmation_controls(entry.read_text(encoding="utf-8"))
                except ResearchDbError as exc:
                    blockers.append(
                        {
                            "reason": "human_literature_confirmation_controls_missing",
                            "path": entry_relative,
                            "detail": str(exc),
                        }
                    )
            else:
                pdf_paths.append(entry)

        for pdf_path in pdf_paths:
            if pdf_path.stem not in stems_with_notes:
                blockers.append(
                    {
                        "reason": "human_literature_pdf_without_note",
                        "path": pdf_path.relative_to(project_root).as_posix(),
                    }
                )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "legacy_paths": sorted(legacy_paths),
    }


def _entity_paper_id(connection, entity_type: str, entity_id: str) -> str | None:
    if entity_type == "paper":
        row = connection.execute("SELECT id FROM papers WHERE id = ?", (entity_id,)).fetchone()
        return str(row["id"]) if row else None
    table = KNOWLEDGE_ENTITY_TABLES.get(entity_type)
    if table is None:
        return None
    row = connection.execute(
        f'SELECT paper_id FROM "{table}" WHERE CAST(id AS TEXT) = ?', (entity_id,)
    ).fetchone()
    return str(row["paper_id"]) if row else None


def literature_completion_readiness(
    project_root: Path, discovery: dict[str, Any] | None = None
) -> dict[str, Any]:
    human_view = literature_human_view_readiness(project_root)
    blockers: list[dict[str, Any]] = list(human_view["blockers"])
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
            "human_view": human_view,
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
        "human_view": human_view,
    }
