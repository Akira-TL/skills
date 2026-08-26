from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect
from research_db_ingest import normalize_doi, normalize_identifier
from research_db_ops.discovery import (
    ACQUISITION_STATUSES,
    IDENTITY_STATUSES,
    READING_PRIORITIES,
    RELEVANCE_STATUSES,
    _db_path,
    _enum,
    _now,
    _text,
)


def update_candidate(project_root: Path, candidate_id: int, changes: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {
        "identity_status",
        "relevance_status",
        "relevance_reason",
        "acquisition_status",
        "reading_priority",
        "exclusion_reason",
        "defer_reason",
        "paper_id",
        "doi",
        "pmid",
        "source_url",
    }
    unknown = sorted(set(changes) - allowed_fields)
    if unknown:
        raise ResearchDbError(f"不支持更新 candidate 字段：{', '.join(unknown)}")
    if not changes:
        raise ResearchDbError("没有 candidate 更新内容。")

    normalized = dict(changes)
    if "identity_status" in normalized:
        normalized["identity_status"] = _enum(
            normalized["identity_status"], IDENTITY_STATUSES, default="unresolved", field="identity_status"
        )
    if "relevance_status" in normalized:
        normalized["relevance_status"] = _enum(
            normalized["relevance_status"], RELEVANCE_STATUSES, default="pending", field="relevance_status"
        )
    if "acquisition_status" in normalized:
        normalized["acquisition_status"] = _enum(
            normalized["acquisition_status"], ACQUISITION_STATUSES, default="pending", field="acquisition_status"
        )
    if "reading_priority" in normalized:
        normalized["reading_priority"] = _enum(
            normalized["reading_priority"], READING_PRIORITIES, default="normal", field="reading_priority"
        )
    if "doi" in normalized:
        normalized["doi"] = normalize_doi(normalized["doi"])
    if "pmid" in normalized:
        normalized["pmid"] = normalize_identifier(normalized["pmid"])
    for field in (
        "relevance_reason",
        "exclusion_reason",
        "defer_reason",
        "paper_id",
        "source_url",
    ):
        if field in normalized:
            normalized[field] = _text(normalized[field])

    with connect(_db_path(project_root)) as connection:
        current = connection.execute(
            "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        if current is None:
            raise ResearchDbError(f"Candidate 不存在：{candidate_id}")
        merged = dict(current)
        merged.update(normalized)
        if merged.get("relevance_status") == "excluded" and not merged.get("exclusion_reason"):
            raise ResearchDbError("excluded candidate 必须提供 exclusion_reason。")
        if merged.get("acquisition_status") == "acquired" and not merged.get("paper_id"):
            raise ResearchDbError("acquired candidate 必须关联 paper_id。")
        if merged.get("paper_id"):
            paper = connection.execute(
                "SELECT id FROM papers WHERE id = ?", (merged["paper_id"],)
            ).fetchone()
            if paper is None:
                raise ResearchDbError(f"Paper 不存在：{merged['paper_id']}")

        for field in ("doi", "pmid"):
            value = merged.get(field)
            if not value:
                continue
            comparator = "lower(doi) = lower(?)" if field == "doi" else "pmid = ?"
            conflict = connection.execute(
                f"SELECT id FROM candidates WHERE id <> ? AND {comparator} ORDER BY id LIMIT 1",
                (candidate_id, value),
            ).fetchone()
            if conflict is not None:
                raise ResearchDbError(
                    f"Candidate {candidate_id} 的 {field} 已存在于 Candidate {conflict['id']}；"
                    "请先使用 merge-candidates 合并身份记录。"
                )

        timestamp = _now()
        assignments = ", ".join(f"{field} = ?" for field in normalized)
        params = [normalized[field] for field in normalized]
        params.extend([timestamp, candidate_id])
        connection.execute(
            f"UPDATE candidates SET {assignments}, updated_at = ? WHERE id = ?", params
        )
        connection.execute(
            """
            INSERT INTO change_log(
                timestamp, action, entity_type, entity_id, paper_id, reason, summary
            ) VALUES (?, 'candidate_updated', 'candidate', ?, ?, ?, ?)
            """,
            (
                timestamp,
                str(candidate_id),
                merged.get("paper_id"),
                normalized.get("relevance_reason") or normalized.get("exclusion_reason"),
                f"Updated candidate fields: {', '.join(sorted(normalized))}",
            ),
        )
        connection.commit()
        row = dict(
            connection.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        )
    if isinstance(row.get("authors"), str):
        try:
            row["authors"] = json.loads(row["authors"])
        except json.JSONDecodeError:
            pass
    return {"ok": True, "candidate": row}


def merge_candidates(
    project_root: Path,
    keep_id: int,
    merge_id: int,
    *,
    reason: str,
) -> dict[str, Any]:
    if keep_id == merge_id:
        raise ResearchDbError("keep_id 与 merge_id 不能相同。")
    merge_reason = _text(reason, required=True, field="merge reason")
    assert merge_reason is not None

    with connect(_db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            keep = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (keep_id,)
            ).fetchone()
            source = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (merge_id,)
            ).fetchone()
            if keep is None:
                raise ResearchDbError(f"Candidate 不存在：{keep_id}")
            if source is None:
                raise ResearchDbError(f"Candidate 不存在：{merge_id}")

            for field in ("doi", "pmid", "paper_id"):
                left = keep[field]
                right = source[field]
                if left and right and str(left).casefold() != str(right).casefold():
                    raise ResearchDbError(
                        f"不能合并 Candidate {keep_id}/{merge_id}：{field} 冲突。"
                    )

            relevance_rank = {"excluded": 0, "pending": 1, "relevant": 2}
            acquisition_rank = {"pending": 0, "queued": 1, "unavailable": 2, "acquired": 3}
            priority_rank = {"low": 0, "normal": 1, "high": 2, "core": 3}
            relevance_status = max(
                (str(keep["relevance_status"]), str(source["relevance_status"])),
                key=relevance_rank.__getitem__,
            )
            acquisition_status = max(
                (str(keep["acquisition_status"]), str(source["acquisition_status"])),
                key=acquisition_rank.__getitem__,
            )
            reading_priority = max(
                (str(keep["reading_priority"]), str(source["reading_priority"])),
                key=priority_rank.__getitem__,
            )
            timestamp = _now()

            connection.execute(
                """
                UPDATE candidates SET
                    doi = COALESCE(NULLIF(doi, ''), ?),
                    pmid = COALESCE(NULLIF(pmid, ''), ?),
                    authors = COALESCE(authors, ?),
                    year = COALESCE(year, ?),
                    source_url = COALESCE(source_url, ?),
                    identity_status = CASE
                        WHEN identity_status = 'resolved' OR ? = 'resolved' THEN 'resolved'
                        ELSE identity_status END,
                    relevance_status = ?,
                    relevance_reason = COALESCE(relevance_reason, ?),
                    paper_id = COALESCE(paper_id, ?),
                    acquisition_status = ?,
                    reading_priority = ?,
                    exclusion_reason = CASE
                        WHEN ? = 'excluded' THEN COALESCE(exclusion_reason, ?)
                        ELSE NULL END,
                    defer_reason = COALESCE(defer_reason, ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    source["doi"],
                    source["pmid"],
                    source["authors"],
                    source["year"],
                    source["source_url"],
                    source["identity_status"],
                    relevance_status,
                    source["relevance_reason"],
                    source["paper_id"],
                    acquisition_status,
                    reading_priority,
                    relevance_status,
                    source["exclusion_reason"],
                    source["defer_reason"],
                    timestamp,
                    keep_id,
                ),
            )

            for link in connection.execute(
                "SELECT * FROM search_run_candidates WHERE candidate_id = ? ORDER BY search_run_id",
                (merge_id,),
            ).fetchall():
                connection.execute(
                    """
                    INSERT INTO search_run_candidates(
                        search_run_id, candidate_id, result_rank, source_result_id,
                        source_url, discovered_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(search_run_id, candidate_id) DO UPDATE SET
                        result_rank = COALESCE(search_run_candidates.result_rank, excluded.result_rank),
                        source_result_id = COALESCE(search_run_candidates.source_result_id, excluded.source_result_id),
                        source_url = COALESCE(search_run_candidates.source_url, excluded.source_url),
                        discovered_at = MIN(search_run_candidates.discovered_at, excluded.discovered_at)
                    """,
                    (
                        link["search_run_id"],
                        keep_id,
                        link["result_rank"],
                        link["source_result_id"],
                        link["source_url"],
                        link["discovered_at"],
                    ),
                )
            connection.execute("DELETE FROM candidates WHERE id = ?", (merge_id,))
            connection.execute(
                """
                INSERT INTO change_log(
                    timestamp, action, entity_type, entity_id, paper_id, reason, summary
                ) VALUES (?, 'candidate_merged', 'candidate', ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    str(keep_id),
                    keep["paper_id"] or source["paper_id"],
                    merge_reason,
                    f"Merged Candidate {merge_id} into Candidate {keep_id}.",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "candidate_id": keep_id,
        "merged_candidate_id": merge_id,
        "reason": merge_reason,
    }


def discovery_readiness(project_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    with connect(_db_path(project_root)) as connection:
        search_count = int(connection.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0])
        candidates = connection.execute(
            "SELECT id, title, doi, pmid, relevance_status, acquisition_status, "
            "reading_priority, defer_reason FROM candidates ORDER BY id"
        ).fetchall()

        for row in candidates:
            if row["relevance_status"] == "pending":
                blockers.append(
                    {
                        "candidate_id": int(row["id"]),
                        "reason": "relevance_pending",
                        "title": row["title"],
                    }
                )
                continue
            if row["relevance_status"] != "relevant":
                continue
            if row["reading_priority"] == "core" and row["acquisition_status"] not in {
                "acquired",
                "unavailable",
            }:
                blockers.append(
                    {
                        "candidate_id": int(row["id"]),
                        "reason": "core_candidate_not_closed",
                        "title": row["title"],
                    }
                )
            elif (
                row["reading_priority"] == "high"
                and row["acquisition_status"] in {"pending", "queued"}
                and not _text(row["defer_reason"])
            ):
                blockers.append(
                    {
                        "candidate_id": int(row["id"]),
                        "reason": "high_priority_candidate_missing_defer_reason",
                        "title": row["title"],
                    }
                )

        for field in ("doi", "pmid"):
            where = "doi IS NOT NULL AND trim(doi) <> ''" if field == "doi" else "pmid IS NOT NULL AND trim(pmid) <> ''"
            normalizer = "lower(doi)" if field == "doi" else "pmid"
            duplicates = connection.execute(
                f"SELECT {normalizer} AS identity, GROUP_CONCAT(id) AS ids, COUNT(*) AS n "
                f"FROM candidates WHERE {where} GROUP BY {normalizer} HAVING COUNT(*) > 1"
            ).fetchall()
            for duplicate in duplicates:
                blockers.append(
                    {
                        "reason": f"duplicate_{field}",
                        "identity": duplicate["identity"],
                        "candidate_ids": [int(value) for value in str(duplicate["ids"]).split(",")],
                    }
                )

    return {
        "ok": True,
        "has_discovery": search_count > 0,
        "search_run_count": search_count,
        "ready_for_saturation": not blockers,
        "blockers": blockers,
    }


def list_candidates(
    project_root: Path,
    *,
    relevance_status: str | None = None,
    acquisition_status: str | None = None,
    reading_priority: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise ResearchDbError("limit 必须在 1 到 100 之间。")
    where: list[str] = []
    params: list[Any] = []
    for field, value, allowed in (
        ("relevance_status", relevance_status, RELEVANCE_STATUSES),
        ("acquisition_status", acquisition_status, ACQUISITION_STATUSES),
        ("reading_priority", reading_priority, READING_PRIORITIES),
    ):
        if value is not None:
            if value not in allowed:
                raise ResearchDbError(f"{field} 必须是：{', '.join(sorted(allowed))}")
            where.append(f"c.{field} = ?")
            params.append(value)
    sql = "SELECT c.* FROM candidates c"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CASE c.reading_priority WHEN 'core' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, c.id LIMIT ?"
    params.append(limit)

    with connect(_db_path(project_root)) as connection:
        rows: list[dict[str, Any]] = []
        for candidate in connection.execute(sql, params):
            row = dict(candidate)
            if isinstance(row.get("authors"), str):
                try:
                    row["authors"] = json.loads(row["authors"])
                except json.JSONDecodeError:
                    pass
            row["search_runs"] = [
                dict(link)
                for link in connection.execute(
                    """
                    SELECT src.search_run_id, src.result_rank, src.source_result_id,
                           src.source_url, sr.source, sr.query, sr.executed_at
                    FROM search_run_candidates src
                    JOIN search_runs sr ON sr.id = src.search_run_id
                    WHERE src.candidate_id = ?
                    ORDER BY src.search_run_id
                    """,
                    (row["id"],),
                )
            ]
            rows.append(row)
    return {"ok": True, "candidates": rows}
