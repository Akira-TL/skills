from __future__ import annotations

import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect, database_path
from research_db_ingest import normalize_doi, normalize_identifier


SEARCH_MODES = {"DISCOVERY", "SYSTEMATIC"}
IDENTITY_STATUSES = {"unresolved", "resolved"}
RELEVANCE_STATUSES = {"pending", "relevant", "excluded"}
ACQUISITION_STATUSES = {"pending", "queued", "acquired", "unavailable"}
READING_PRIORITIES = {"core", "high", "normal", "low"}
DISCOVERY_METHODS = {
    "seed_search",
    "query_expansion",
    "backward_citation",
    "forward_citation",
    "related_work",
    "method_search",
    "update_search",
    "exact_work",
    "other",
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


def _enum(value: object, allowed: set[str], *, default: str, field: str) -> str:
    text = _text(value) or default
    if text not in allowed:
        raise ResearchDbError(f"{field} 必须是：{', '.join(sorted(allowed))}")
    return text


def _authors(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        return value.strip() or None
    raise ResearchDbError("candidate authors 必须是字符串或字符串数组。")


def _year(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        year = int(value)
    except (TypeError, ValueError) as exc:
        raise ResearchDbError("candidate year 必须是整数。") from exc
    if year < 1000 or year > 3000:
        raise ResearchDbError("candidate year 超出合理范围。")
    return year


def _title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in normalized).split())


def _title_match(
    connection: sqlite3.Connection,
    *,
    title: str,
    year: int | None,
    unresolved_only: bool,
) -> sqlite3.Row | None:
    where = ["((year IS NULL AND ? IS NULL) OR year = ?)"]
    params: list[Any] = [year, year]
    if unresolved_only:
        where.extend(
            [
                "(doi IS NULL OR trim(doi) = '')",
                "(pmid IS NULL OR trim(pmid) = '')",
            ]
        )
    rows = connection.execute(
        "SELECT * FROM candidates WHERE " + " AND ".join(where) + " ORDER BY id",
        params,
    ).fetchall()
    key = _title_key(title)
    return next((row for row in rows if _title_key(str(row["title"])) == key), None)


def _existing_paper(
    connection: sqlite3.Connection, doi: str | None, pmid: str | None
) -> str | None:
    if doi:
        row = connection.execute(
            "SELECT id FROM papers WHERE lower(doi) = lower(?)", (doi,)
        ).fetchone()
        if row:
            return str(row["id"])
    if pmid:
        row = connection.execute("SELECT id FROM papers WHERE pmid = ?", (pmid,)).fetchone()
        if row:
            return str(row["id"])
    return None


def _find_candidate(
    connection: sqlite3.Connection,
    *,
    title: str,
    doi: str | None,
    pmid: str | None,
    year: int | None,
) -> sqlite3.Row | None:
    if doi:
        row = connection.execute(
            "SELECT * FROM candidates WHERE lower(doi) = lower(?) ORDER BY id LIMIT 1",
            (doi,),
        ).fetchone()
        if row:
            return row
    if pmid:
        row = connection.execute(
            "SELECT * FROM candidates WHERE pmid = ? ORDER BY id LIMIT 1", (pmid,)
        ).fetchone()
        if row:
            return row

    # Identity resolution often changes punctuation/capitalization in titles. Reuse a
    # normalized unresolved title match, but never merge two conflicting stable IDs.
    if doi or pmid:
        return _title_match(
            connection, title=title, year=year, unresolved_only=True
        )

    return _title_match(connection, title=title, year=year, unresolved_only=False)


def _record_candidate(
    connection: sqlite3.Connection,
    run_id: int,
    raw: dict[str, Any],
    *,
    discovery_source: str,
    timestamp: str,
) -> dict[str, Any]:
    title = _text(raw.get("title"), required=True, field="candidate title")
    assert title is not None
    doi = normalize_doi(raw.get("doi"))
    pmid = normalize_identifier(raw.get("pmid"))
    year = _year(raw.get("year"))
    authors = _authors(raw.get("authors"))
    source_url = _text(raw.get("source_url"))
    identity_status = _enum(
        raw.get("identity_status"),
        IDENTITY_STATUSES,
        default="resolved" if (doi or pmid) else "unresolved",
        field="identity_status",
    )
    relevance_status = _enum(
        raw.get("relevance_status"),
        RELEVANCE_STATUSES,
        default="pending",
        field="relevance_status",
    )
    acquisition_status = _enum(
        raw.get("acquisition_status"),
        ACQUISITION_STATUSES,
        default="queued" if relevance_status == "relevant" else "pending",
        field="acquisition_status",
    )
    if acquisition_status == "unavailable":
        raise ResearchDbError(
            "Search Run 不能直接创建 acquisition_status=unavailable 的 Candidate；"
            "先保留为 queued，记录 Acquisition Attempt provenance 后再 update-candidate。"
        )
    reading_priority = _enum(
        raw.get("reading_priority"),
        READING_PRIORITIES,
        default="normal",
        field="reading_priority",
    )
    relevance_reason = _text(raw.get("relevance_reason"))
    exclusion_reason = _text(raw.get("exclusion_reason"))
    if relevance_status == "excluded" and not exclusion_reason:
        raise ResearchDbError("excluded candidate 必须提供 exclusion_reason。")

    paper_id = _existing_paper(connection, doi, pmid)
    if paper_id:
        identity_status = "resolved"
        acquisition_status = "acquired"

    existing = _find_candidate(
        connection, title=title, doi=doi, pmid=pmid, year=year
    )
    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO candidates(
                title, doi, pmid, authors, year, discovery_source,
                identity_status, relevance_status, relevance_reason, paper_id,
                created_at, updated_at, source_url, acquisition_status,
                reading_priority, exclusion_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                doi,
                pmid,
                authors,
                year,
                discovery_source,
                identity_status,
                relevance_status,
                relevance_reason,
                paper_id,
                timestamp,
                timestamp,
                source_url,
                acquisition_status,
                reading_priority,
                exclusion_reason,
            ),
        )
        candidate_id = int(cursor.lastrowid)
        action = "created"
    else:
        candidate_id = int(existing["id"])
        connection.execute(
            """
            UPDATE candidates SET
                title = ?,
                doi = COALESCE(NULLIF(doi, ''), ?),
                pmid = COALESCE(NULLIF(pmid, ''), ?),
                authors = COALESCE(authors, ?),
                year = COALESCE(year, ?),
                source_url = COALESCE(source_url, ?),
                identity_status = CASE
                    WHEN identity_status = 'resolved' OR ? = 'resolved' THEN 'resolved'
                    ELSE identity_status END,
                relevance_status = CASE
                    WHEN relevance_status = 'pending' THEN ? ELSE relevance_status END,
                relevance_reason = COALESCE(relevance_reason, ?),
                paper_id = COALESCE(paper_id, ?),
                acquisition_status = CASE
                    WHEN ? = 'acquired' THEN 'acquired'
                    WHEN acquisition_status = 'pending' THEN ?
                    ELSE acquisition_status END,
                reading_priority = CASE
                    WHEN reading_priority = 'normal' THEN ? ELSE reading_priority END,
                exclusion_reason = COALESCE(exclusion_reason, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                doi,
                pmid,
                authors,
                year,
                source_url,
                identity_status,
                relevance_status,
                relevance_reason,
                paper_id,
                acquisition_status,
                acquisition_status,
                reading_priority,
                exclusion_reason,
                timestamp,
                candidate_id,
            ),
        )
        action = "reused"

    result_rank = raw.get("result_rank")
    if result_rank is not None:
        try:
            result_rank = int(result_rank)
        except (TypeError, ValueError) as exc:
            raise ResearchDbError("result_rank 必须是整数。") from exc
        if result_rank < 1:
            raise ResearchDbError("result_rank 必须 >= 1。")

    connection.execute(
        """
        INSERT INTO search_run_candidates(
            search_run_id, candidate_id, result_rank, source_result_id,
            source_url, discovered_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(search_run_id, candidate_id) DO UPDATE SET
            result_rank = COALESCE(excluded.result_rank, result_rank),
            source_result_id = COALESCE(excluded.source_result_id, source_result_id),
            source_url = COALESCE(excluded.source_url, source_url)
        """,
        (
            run_id,
            candidate_id,
            result_rank,
            _text(raw.get("source_result_id")),
            source_url,
            timestamp,
        ),
    )
    connection.execute(
        """
        INSERT INTO change_log(
            timestamp, action, entity_type, entity_id, paper_id, reason, run_id, summary
        ) VALUES (?, ?, 'candidate', ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            f"candidate_{action}",
            str(candidate_id),
            paper_id,
            relevance_reason,
            run_id,
            f"{action} discovery candidate: {title}",
        ),
    )
    return {"id": candidate_id, "action": action, "title": title, "paper_id": paper_id}


def record_search_run(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    purpose = _text(bundle.get("purpose"), required=True, field="purpose")
    source = _text(bundle.get("source"), required=True, field="source")
    query = _text(bundle.get("query"), required=True, field="query")
    assert purpose is not None and source is not None and query is not None
    mode = _text(bundle.get("mode")) or "DISCOVERY"
    mode = mode.upper()
    if mode not in SEARCH_MODES:
        raise ResearchDbError("mode 必须是 DISCOVERY 或 SYSTEMATIC。")
    discovery_method = _text(bundle.get("discovery_method"))
    if mode == "DISCOVERY":
        if discovery_method not in DISCOVERY_METHODS:
            raise ResearchDbError(
                "DISCOVERY Search Run 必须显式提供 discovery_method："
                + ", ".join(sorted(DISCOVERY_METHODS))
            )
    else:
        discovery_method = discovery_method or "other"
        if discovery_method not in DISCOVERY_METHODS:
            raise ResearchDbError(
                "discovery_method 必须是：" + ", ".join(sorted(DISCOVERY_METHODS))
            )

    raw_candidates = bundle.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise ResearchDbError("candidates 必须是数组。")
    if not all(isinstance(item, dict) for item in raw_candidates):
        raise ResearchDbError("每个 candidate 必须是 JSON object。")

    parent_run_id = bundle.get("parent_run_id")
    if parent_run_id is not None:
        try:
            parent_run_id = int(parent_run_id)
        except (TypeError, ValueError) as exc:
            raise ResearchDbError("parent_run_id 必须是整数。") from exc

    timestamp = _text(bundle.get("executed_at")) or _now()
    result_count = bundle.get("result_count")
    if result_count is None:
        result_count = len(raw_candidates)
    try:
        result_count = int(result_count)
    except (TypeError, ValueError) as exc:
        raise ResearchDbError("result_count 必须是整数。") from exc
    if result_count < len(raw_candidates):
        raise ResearchDbError("result_count 不能小于持久化 candidates 数量。")

    filters = bundle.get("filters")
    if filters is not None and not isinstance(filters, str):
        filters = json.dumps(filters, ensure_ascii=False, sort_keys=True)

    with connect(_db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            if parent_run_id is not None:
                parent = connection.execute(
                    "SELECT id FROM search_runs WHERE id = ?", (parent_run_id,)
                ).fetchone()
                if parent is None:
                    raise ResearchDbError(f"parent search run 不存在：{parent_run_id}")
            cursor = connection.execute(
                """
                INSERT INTO search_runs(
                    purpose, mode, source, query, filters, parent_run_id, reason,
                    executed_at, result_count, what_we_learned, next_decision,
                    discovery_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    purpose,
                    mode,
                    source,
                    query,
                    filters,
                    parent_run_id,
                    _text(bundle.get("reason")),
                    timestamp,
                    result_count,
                    _text(bundle.get("what_we_learned")),
                    _text(bundle.get("next_decision")),
                    discovery_method,
                ),
            )
            run_id = int(cursor.lastrowid)
            candidates = [
                _record_candidate(
                    connection,
                    run_id,
                    raw,
                    discovery_source=source,
                    timestamp=timestamp,
                )
                for raw in raw_candidates
            ]
            connection.execute(
                """
                INSERT INTO change_log(
                    timestamp, action, entity_type, entity_id, reason, run_id, summary
                ) VALUES (?, 'search_recorded', 'search_run', ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    str(run_id),
                    _text(bundle.get("reason")),
                    run_id,
                    f"Recorded {mode} search with {len(candidates)} persisted candidates.",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "search_run_id": run_id,
        "mode": mode,
        "discovery_method": discovery_method,
        "result_count": result_count,
        "persisted_candidates": candidates,
    }


def list_search_runs(project_root: Path, *, limit: int = 50) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise ResearchDbError("limit 必须在 1 到 100 之间。")
    with connect(_db_path(project_root)) as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM search_runs ORDER BY id DESC LIMIT ?", (limit,)
            )
        ]
    for row in rows:
        if isinstance(row.get("filters"), str):
            try:
                row["filters"] = json.loads(row["filters"])
            except json.JSONDecodeError:
                pass
    return {"ok": True, "search_runs": rows}


