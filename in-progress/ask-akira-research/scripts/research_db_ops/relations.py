from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect, database_path


ENTITY_TABLES = {
    "method": "methods",
    "experiment": "experiments",
    "observation": "observations",
    "claim": "claims",
    "issue": "issues",
    "lead": "leads",
}
ALLOWED_ENTITY_TYPES = {"paper", *ENTITY_TABLES}
ALLOWED_PREDICATES = {
    "USES",
    "PRODUCES",
    "DIRECTLY_SUPPORTS",
    "INDIRECTLY_SUPPORTS",
    "QUALIFIES",
    "CONTRADICTS",
    "DOES_NOT_TEST",
    "LIMITS",
    "CHALLENGES",
    "WEAKENS",
    "SHARES_SAMPLES_WITH",
    "SHARES_DATA_WITH",
    "CITES",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(project_root: Path) -> Path:
    path = database_path(project_root)
    if not path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")
    return path


def _text(value: object, *, required: bool = False, field: str = "字段") -> str | None:
    if value is None:
        if required:
            raise ResearchDbError(f"{field} 不能为空。")
        return None
    text = str(value).strip()
    if not text and required:
        raise ResearchDbError(f"{field} 不能为空。")
    return text or None


def _resolve_entity(connection, entity_type: str, entity_id: str) -> tuple[str, str]:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise ResearchDbError(f"不支持的 relation entity type：{entity_type}")
    if entity_type == "paper":
        row = connection.execute("SELECT id FROM papers WHERE id = ?", (entity_id,)).fetchone()
        if row is None:
            raise ResearchDbError(f"Paper 不存在：{entity_id}")
        return entity_id, entity_id

    table = ENTITY_TABLES[entity_type]
    row = connection.execute(
        f'SELECT paper_id FROM "{table}" WHERE CAST(id AS TEXT) = ?', (entity_id,)
    ).fetchone()
    if row is None:
        raise ResearchDbError(f"实体不存在：{entity_type}:{entity_id}")
    return entity_id, str(row["paper_id"])


def add_relation(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    subject_type = _text(bundle.get("subject_type"), required=True, field="subject_type")
    subject_id = _text(bundle.get("subject_id"), required=True, field="subject_id")
    predicate = _text(bundle.get("predicate"), required=True, field="predicate")
    object_type = _text(bundle.get("object_type"), required=True, field="object_type")
    object_id = _text(bundle.get("object_id"), required=True, field="object_id")
    note = _text(bundle.get("note"), required=True, field="note")
    assert subject_type and subject_id and predicate and object_type and object_id and note

    predicate = predicate.upper()
    if predicate == "SUPPORTS":
        raise ResearchDbError(
            "科研证据关系不得使用模糊 SUPPORTS；请明确 DIRECTLY_SUPPORTS 或 INDIRECTLY_SUPPORTS。"
        )
    if predicate not in ALLOWED_PREDICATES:
        raise ResearchDbError(f"不支持的 relation predicate：{predicate}")
    if subject_type == object_type and subject_id == object_id:
        raise ResearchDbError("relation 不能连接实体自身。")

    confidence = _text(bundle.get("confidence"))
    reason = _text(bundle.get("reason")) or "Verified cross-entity research relation"
    timestamp = _text(bundle.get("created_at")) or _now()

    with connect(_db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            subject_id, subject_paper = _resolve_entity(connection, subject_type, subject_id)
            object_id, object_paper = _resolve_entity(connection, object_type, object_id)
            duplicate = connection.execute(
                """
                SELECT id FROM relations
                WHERE subject_type = ? AND subject_id = ? AND predicate = ?
                  AND object_type = ? AND object_id = ?
                LIMIT 1
                """,
                (subject_type, subject_id, predicate, object_type, object_id),
            ).fetchone()
            if duplicate is not None:
                raise ResearchDbError(f"relation 已存在：{int(duplicate['id'])}")

            cursor = connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id,
                    confidence, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subject_type,
                    subject_id,
                    predicate,
                    object_type,
                    object_id,
                    confidence,
                    note,
                    timestamp,
                ),
            )
            relation_id = int(cursor.lastrowid)
            touched_papers = list(dict.fromkeys([subject_paper, object_paper]))
            for paper_id in touched_papers:
                connection.execute(
                    """
                    INSERT INTO change_log(
                        timestamp, action, entity_type, entity_id, paper_id, reason, summary
                    ) VALUES (?, 'ADD', 'relation', ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        str(relation_id),
                        paper_id,
                        reason,
                        f"{subject_type}:{subject_id} {predicate} {object_type}:{object_id}",
                    ),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "relation": {
            "id": relation_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "predicate": predicate,
            "object_type": object_type,
            "object_id": object_id,
            "confidence": confidence,
            "note": note,
            "created_at": timestamp,
        },
        "paper_ids": touched_papers,
    }
