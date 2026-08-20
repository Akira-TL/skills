from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from research_db_core import ResearchDbError, connect, database_path


ENTITY_TABLES = {
    "method": "methods",
    "experiment": "experiments",
    "observation": "observations",
    "claim": "claims",
    "issue": "issues",
    "lead": "leads",
}
SEARCH_ENTITY_TYPES = {"paper", *ENTITY_TABLES}
JSON_FIELDS = {
    "paper": {"authors"},
    "method": {"parameters", "materials", "software"},
    "experiment": {"groups_json", "variables_json"},
    "observation": {"statistics_json"},
}


def _db_path(project_root: Path) -> Path:
    path = database_path(project_root)
    if not path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")
    return path


def _limit(value: int) -> int:
    if value < 1 or value > 100:
        raise ResearchDbError("limit 必须在 1 到 100 之间。")
    return value


def _fts_query(value: str) -> str:
    query = value.strip()
    if not query:
        raise ResearchDbError("查询不能为空。")
    tokens = re.findall(r"[^\s\"'():*+]+", query, flags=re.UNICODE)
    tokens = [token.strip("-,") for token in tokens]
    tokens = [token for token in tokens if token]
    if not tokens:
        raise ResearchDbError("查询没有可检索词。")
    return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


def _parse_json_fields(entity_type: str, record: dict[str, Any]) -> dict[str, Any]:
    for field in JSON_FIELDS.get(entity_type, set()):
        value = record.get(field)
        if not isinstance(value, str) or not value:
            continue
        try:
            record[field] = json.loads(value)
        except json.JSONDecodeError:
            pass
    return record


def _source_for_record(
    connection: sqlite3.Connection, record: dict[str, Any]
) -> dict[str, Any] | None:
    artifact_id = record.get("artifact_id")
    locator = record.get("source_locator")
    if artifact_id is None and locator is None:
        return None
    source: dict[str, Any] = {
        "artifact_id": artifact_id,
        "source_locator": locator,
    }
    if artifact_id is not None:
        row = connection.execute(
            "SELECT kind, path, version, source, source_url FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
        if row is not None:
            source.update(dict(row))
    return source


def _entity_record(
    connection: sqlite3.Connection, entity_type: str, entity_id: str
) -> dict[str, Any] | None:
    if entity_type == "paper":
        row = connection.execute("SELECT * FROM papers WHERE id = ?", (entity_id,)).fetchone()
    else:
        table = ENTITY_TABLES.get(entity_type)
        if table is None:
            raise ResearchDbError(f"不支持的实体类型：{entity_type}")
        row = connection.execute(
            f'SELECT * FROM "{table}" WHERE CAST(id AS TEXT) = ?', (entity_id,)
        ).fetchone()
    if row is None:
        return None

    record = _parse_json_fields(entity_type, dict(row))
    record["entity_type"] = entity_type
    record["entity_id"] = str(record["id"])
    if entity_type != "paper":
        source = _source_for_record(connection, record)
        if source is not None:
            record["source"] = source
    return record


def _normalize_entity_types(entity_types: Iterable[str] | None) -> list[str]:
    if entity_types is None:
        return []
    normalized = list(dict.fromkeys(entity_types))
    unknown = sorted(set(normalized) - SEARCH_ENTITY_TYPES)
    if unknown:
        raise ResearchDbError(f"不支持的实体类型：{', '.join(unknown)}")
    return normalized


def search_knowledge(
    project_root: Path,
    query: str,
    *,
    entity_types: Iterable[str] | None = None,
    paper_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    limit = _limit(limit)
    types = _normalize_entity_types(entity_types)
    match_query = _fts_query(query)
    where = ["knowledge_fts MATCH ?"]
    params: list[Any] = [match_query]
    if types:
        placeholders = ", ".join("?" for _ in types)
        where.append(f"entity_type IN ({placeholders})")
        params.extend(types)
    if paper_id:
        where.append("paper_id = ?")
        params.append(paper_id)
    params.append(limit)

    sql = f"""
        SELECT entity_type, entity_id, paper_id, title,
               snippet(knowledge_fts, 4, '[', ']', ' … ', 20) AS snippet,
               bm25(knowledge_fts) AS retrieval_rank
        FROM knowledge_fts
        WHERE {' AND '.join(where)}
        ORDER BY retrieval_rank, entity_type, entity_id
        LIMIT ?
    """
    with connect(_db_path(project_root)) as connection:
        matches = connection.execute(sql, params).fetchall()
        results: list[dict[str, Any]] = []
        for match in matches:
            record = _entity_record(
                connection, str(match["entity_type"]), str(match["entity_id"])
            )
            if record is None:
                continue
            record["retrieval_rank"] = float(match["retrieval_rank"])
            record["snippet"] = match["snippet"]
            results.append(record)

    return {
        "ok": True,
        "query": query,
        "entity_types": types or None,
        "paper_id": paper_id,
        "results": results,
    }


def evidence_packet(
    project_root: Path,
    query: str,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Return a provenance-preserving evidence packet, not an evidence judgment."""
    matches = search_knowledge(
        project_root,
        query,
        entity_types=["claim", "observation", "issue"],
        limit=limit,
    )
    entity_keys = {
        (item["entity_type"], item["entity_id"])
        for item in matches["results"]
    }

    with connect(_db_path(project_root)) as connection:
        relations: list[dict[str, Any]] = []
        if entity_keys:
            predicates: list[str] = []
            params: list[str] = []
            for entity_type, entity_id in entity_keys:
                predicates.append("(subject_type = ? AND subject_id = ?)")
                predicates.append("(object_type = ? AND object_id = ?)")
                params.extend([entity_type, entity_id, entity_type, entity_id])
            sql = "SELECT * FROM relations WHERE " + " OR ".join(predicates) + " ORDER BY id"
            for row in connection.execute(sql, params):
                relations.append(dict(row))

    return {
        "ok": True,
        "query": query,
        "evidence_units": matches["results"],
        "relations": relations,
        "note": "该结果仅检索证据单元与关系，不代表科研结论强度判断。",
    }


def list_entities(
    project_root: Path,
    entity_type: str,
    *,
    query: str | None = None,
    paper_id: str | None = None,
    limit: int = 50,
    severity: str | None = None,
    nature: str | None = None,
) -> dict[str, Any]:
    limit = _limit(limit)
    if entity_type not in ENTITY_TABLES:
        raise ResearchDbError(f"不支持的实体类型：{entity_type}")
    if query:
        result = search_knowledge(
            project_root,
            query,
            entity_types=[entity_type],
            paper_id=paper_id,
            limit=limit,
        )
        if entity_type == "issue":
            result["results"] = [
                row
                for row in result["results"]
                if (severity is None or row.get("severity") == severity)
                and (nature is None or row.get("nature") == nature)
            ]
        return result

    table = ENTITY_TABLES[entity_type]
    where: list[str] = []
    params: list[Any] = []
    if paper_id:
        where.append("paper_id = ?")
        params.append(paper_id)
    if entity_type == "issue" and severity:
        where.append("severity = ?")
        params.append(severity)
    if entity_type == "issue" and nature:
        where.append("nature = ?")
        params.append(nature)
    params.append(limit)
    sql = f'SELECT id FROM "{table}"'
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY paper_id, id LIMIT ?"

    with connect(_db_path(project_root)) as connection:
        ids = [str(row["id"]) for row in connection.execute(sql, params)]
        results = [
            record
            for entity_id in ids
            if (record := _entity_record(connection, entity_type, entity_id)) is not None
        ]
    return {
        "ok": True,
        "entity_type": entity_type,
        "query": None,
        "paper_id": paper_id,
        "results": results,
    }


def get_paper(project_root: Path, paper_id: str) -> dict[str, Any]:
    with connect(_db_path(project_root)) as connection:
        paper = _entity_record(connection, "paper", paper_id)
        if paper is None:
            raise ResearchDbError(f"Paper 不存在：{paper_id}")
        artifacts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM artifacts WHERE paper_id = ? ORDER BY id", (paper_id,)
            )
        ]
        reading_runs: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT * FROM reading_runs WHERE paper_id = ? ORDER BY id", (paper_id,)
        ):
            run = dict(row)
            for field in ("artifacts_checked", "sections_checked"):
                if isinstance(run.get(field), str) and run[field]:
                    try:
                        run[field] = json.loads(run[field])
                    except json.JSONDecodeError:
                        pass
            reading_runs.append(run)
        counts = {
            table: int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE paper_id = ?', (paper_id,)
                ).fetchone()[0]
            )
            for table in (*ENTITY_TABLES.values(), "reading_runs")
        }
    return {
        "ok": True,
        "paper": paper,
        "artifacts": artifacts,
        "reading_runs": reading_runs,
        "counts": counts,
    }
