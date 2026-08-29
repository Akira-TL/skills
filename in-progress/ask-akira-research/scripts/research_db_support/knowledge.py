from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from research_db_support.checks import source_locator_is_specific
from research_db_support.schema import KNOWLEDGE_ENTITY_TABLES
from research_db_support.storage import ResearchDbError


DEPTH_ORDER = {"none": 0, "full_scan": 1, "deep_extraction": 2}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: object, *, required: bool = False, field: str = "value") -> str | None:
    if value is None:
        if required:
            raise ResearchDbError(f"{field} 不能为空。")
        return None
    result = str(value).strip()
    if required and not result:
        raise ResearchDbError(f"{field} 不能为空。")
    return result or None


def json_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def array(bundle: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = bundle.get(field, [])
    if not isinstance(value, list):
        raise ResearchDbError(f"{field} 必须是 JSON array。")
    if not all(isinstance(item, dict) for item in value):
        raise ResearchDbError(f"{field} 的每一项必须是 JSON object。")
    return value


def string_list(value: object, field: str, *, required: bool = False) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ResearchDbError(f"{field} 必须是非空字符串数组。")
    result = [item.strip() for item in value]
    if required and not result:
        raise ResearchDbError(f"{field} 至少需要一项。")
    return result


def paper(connection: sqlite3.Connection, paper_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if row is None:
        raise ResearchDbError(f"Paper 不存在：{paper_id}")
    return row


def _artifact_id(
    connection: sqlite3.Connection,
    paper_id: str,
    spec: dict[str, Any],
) -> int | None:
    raw_id = spec.get("artifact_id")
    raw_path = text(spec.get("artifact_path"))
    raw_kind = text(spec.get("artifact_kind"))
    selectors = sum(value is not None for value in (raw_id, raw_path, raw_kind))
    if selectors == 0:
        return None
    if selectors > 1:
        raise ResearchDbError(
            "artifact_id / artifact_path / artifact_kind 只能提供一种定位方式。"
        )

    if raw_id is not None:
        try:
            artifact_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ResearchDbError("artifact_id 必须是整数。") from exc
        row = connection.execute(
            "SELECT id FROM artifacts WHERE id = ? AND paper_id = ?",
            (artifact_id, paper_id),
        ).fetchone()
        if row is None:
            raise ResearchDbError(f"artifact_id={artifact_id} 不属于 {paper_id}。")
        return artifact_id

    if raw_path is not None:
        rows = connection.execute(
            "SELECT id FROM artifacts WHERE paper_id = ? AND path = ?",
            (paper_id, raw_path),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id FROM artifacts WHERE paper_id = ? AND kind = ?",
            (paper_id, raw_kind),
        ).fetchall()

    if len(rows) != 1:
        label = f"path={raw_path!r}" if raw_path is not None else f"kind={raw_kind!r}"
        raise ResearchDbError(f"{paper_id} 的 artifact {label} 解析到 {len(rows)} 条记录。")
    return int(rows[0]["id"])


def checked_artifacts(
    connection: sqlite3.Connection, paper_id: str, value: object
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ResearchDbError("artifacts_checked 至少需要一个 artifact。")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise ResearchDbError(f"artifacts_checked #{index} 必须是 JSON object。")
        artifact_id = _artifact_id(connection, paper_id, raw)
        if artifact_id is None:
            raise ResearchDbError(f"artifacts_checked #{index} 缺少 artifact locator。")
        row = connection.execute(
            "SELECT id, kind, path FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        normalized.append(
            {"id": int(row["id"]), "kind": row["kind"], "path": row["path"]}
        )
    return normalized


def source_fields(
    connection: sqlite3.Connection,
    paper_id: str,
    spec: dict[str, Any],
    *,
    required: bool = False,
    field: str = "knowledge unit",
) -> tuple[int | None, str | None]:
    artifact_id = _artifact_id(connection, paper_id, spec)
    source_locator = text(spec.get("source_locator"))
    if required and artifact_id is None:
        raise ResearchDbError(f"{field} 必须定位到具体 artifact。")
    if required and source_locator is None:
        raise ResearchDbError(f"{field} 必须提供 source_locator。")
    if required and source_locator is not None and not source_locator_is_specific(source_locator):
        raise ResearchDbError(
            f"{field} 的 source_locator={source_locator!r} 过于模糊；"
            "至少定位到具体 subsection、page、figure/table、supplement item 或等价的唯一位置。"
        )
    return artifact_id, source_locator


def register_ref(
    refs: dict[tuple[str, str], str], entity_type: str, spec: dict[str, Any], entity_id: int
) -> None:
    ref = text(spec.get("ref"), required=True, field=f"{entity_type}.ref")
    key = (entity_type, ref)
    if key in refs:
        raise ResearchDbError(f"重复 bundle ref：{entity_type}:{ref}")
    refs[key] = str(entity_id)


def _existing_entity_for_paper(
    connection: sqlite3.Connection, paper_id: str, entity_type: str, entity_id: str
) -> bool:
    if entity_type == "paper":
        return entity_id == paper_id
    table = KNOWLEDGE_ENTITY_TABLES.get(entity_type)
    if table is None:
        return False
    row = connection.execute(
        f'SELECT 1 FROM "{table}" WHERE CAST(id AS TEXT) = ? AND paper_id = ?',
        (entity_id, paper_id),
    ).fetchone()
    return row is not None


def resolve_entity(
    connection: sqlite3.Connection,
    paper_id: str,
    refs: dict[tuple[str, str], str],
    spec: dict[str, Any],
    prefix: str,
) -> tuple[str, str]:
    entity_type = text(
        spec.get(f"{prefix}_type"), required=True, field=f"{prefix}_type"
    )
    raw_ref = text(spec.get(f"{prefix}_ref"))
    raw_id = text(spec.get(f"{prefix}_id"))
    if bool(raw_ref) == bool(raw_id):
        raise ResearchDbError(
            f"{prefix} 必须且只能提供 {prefix}_ref 或 {prefix}_id。"
        )
    if raw_ref:
        key = (entity_type, raw_ref)
        if key not in refs:
            raise ResearchDbError(f"未知 bundle ref：{entity_type}:{raw_ref}")
        entity_id = refs[key]
    else:
        entity_id = raw_id
    if not _existing_entity_for_paper(connection, paper_id, entity_type, entity_id):
        raise ResearchDbError(
            f"{prefix} 不属于 {paper_id} 或不存在：{entity_type}:{entity_id}"
        )
    return entity_type, entity_id


def write_change(
    connection: sqlite3.Connection,
    *,
    timestamp: str,
    entity_type: str,
    entity_id: str,
    paper_id: str,
    reason: str,
    run_id: int | None,
    summary: str,
) -> None:
    connection.execute(
        """
        INSERT INTO change_log(
            timestamp, action, entity_type, entity_id, paper_id, reason, run_id, summary
        ) VALUES (?, 'ADD', ?, ?, ?, ?, ?, ?)
        """,
        (timestamp, entity_type, entity_id, paper_id, reason, run_id, summary),
    )


def insert_relations(
    connection: sqlite3.Connection,
    paper_id: str,
    refs: dict[tuple[str, str], str],
    relations: list[dict[str, Any]],
    timestamp: str,
    reason: str,
    run_id: int,
) -> int:
    count = 0
    for spec in relations:
        subject_type, subject_id = resolve_entity(
            connection, paper_id, refs, spec, "subject"
        )
        object_type, object_id = resolve_entity(
            connection, paper_id, refs, spec, "object"
        )
        predicate = text(spec.get("predicate"), required=True, field="predicate")
        note = text(spec.get("note"))
        if predicate == "SUPPORTS":
            raise ResearchDbError(
                "科研证据关系不得使用模糊 SUPPORTS；请明确 DIRECTLY_SUPPORTS 或 INDIRECTLY_SUPPORTS。"
            )
        if predicate in {"INDIRECTLY_SUPPORTS", "QUALIFIES", "DOES_NOT_TEST"} and note is None:
            raise ResearchDbError(f"{predicate} relation 必须说明证据边界 note。")
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
                text(spec.get("confidence")),
                note,
                timestamp,
            ),
        )
        relation_id = int(cursor.lastrowid)
        write_change(
            connection,
            timestamp=timestamp,
            entity_type="relation",
            entity_id=str(relation_id),
            paper_id=paper_id,
            reason=reason,
            run_id=run_id,
            summary=f"{subject_type}:{subject_id} {predicate} {object_type}:{object_id}",
        )
        count += 1
    return count


def depth(current: str, requested: str) -> str:
    if requested not in DEPTH_ORDER:
        raise ResearchDbError("depth 必须是 full_scan 或 deep_extraction。")
    return requested if DEPTH_ORDER[requested] >= DEPTH_ORDER[current] else current


