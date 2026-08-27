from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect
from research_db_ops.discovery import _db_path, _enum, _now, _text


TARGET_KINDS = {"main_text", "supplement", "code_data"}
ROUTE_FAMILIES = {"publisher", "open_index", "repository", "preprint", "authenticated", "other"}
RESOURCE_KINDS = {"article_page", "full_text_html", "pdf", "xml", "repository_record", "supplement", "other"}
OUTCOMES = {
    "acquired",
    "not_found",
    "access_denied",
    "auth_required",
    "challenge",
    "invalid_artifact",
    "network_error",
    "other_failure",
}
FAILURE_OUTCOMES = OUTCOMES - {"acquired"}


def _optional_int(value: object, *, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ResearchDbError(f"{field} 必须是整数。") from exc
    if result < 1:
        raise ResearchDbError(f"{field} 必须 >= 1。")
    return result


def record_acquisition_attempt(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    candidate_id = _optional_int(bundle.get("candidate_id"), field="candidate_id")
    paper_id = _text(bundle.get("paper_id"))
    if candidate_id is None and paper_id is None:
        raise ResearchDbError("Acquisition Attempt 必须至少关联 candidate_id 或 paper_id。")

    target_kind = _enum(bundle.get("target_kind"), TARGET_KINDS, default="main_text", field="target_kind")
    route_family = _enum(bundle.get("route_family"), ROUTE_FAMILIES, default="other", field="route_family")
    resource_kind = _enum(bundle.get("resource_kind"), RESOURCE_KINDS, default="other", field="resource_kind")
    outcome = _enum(bundle.get("outcome"), OUTCOMES, default="other_failure", field="outcome")
    target_label = _text(bundle.get("target_label"))
    source_url = _text(bundle.get("source_url"), required=True, field="source_url")
    detail = _text(bundle.get("detail"), required=True, field="detail")
    attempted_at = _text(bundle.get("attempted_at")) or _now()
    assert source_url is not None and detail is not None

    if target_kind != "main_text" and paper_id is None:
        raise ResearchDbError(f"target_kind={target_kind} 的 Acquisition Attempt 必须关联 paper_id。")
    if target_kind == "supplement" and target_label is None:
        raise ResearchDbError("supplement Acquisition Attempt 必须提供 target_label。")

    with connect(_db_path(project_root)) as connection:
        if candidate_id is not None:
            candidate = connection.execute(
                "SELECT id, paper_id FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
            if candidate is None:
                raise ResearchDbError(f"Candidate 不存在：{candidate_id}")
            if paper_id is not None and candidate["paper_id"] not in {None, paper_id}:
                raise ResearchDbError(
                    f"Candidate {candidate_id} 已关联 {candidate['paper_id']}，与 attempt.paper_id={paper_id} 不一致。"
                )
        if paper_id is not None:
            paper = connection.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
            if paper is None:
                raise ResearchDbError(f"Paper 不存在：{paper_id}")

        cursor = connection.execute(
            """
            INSERT INTO acquisition_attempts(
                candidate_id, paper_id, target_kind, target_label, route_family,
                resource_kind, source_url, outcome, detail, attempted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                paper_id,
                target_kind,
                target_label,
                route_family,
                resource_kind,
                source_url,
                outcome,
                detail,
                attempted_at,
            ),
        )
        attempt_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO change_log(
                timestamp, action, entity_type, entity_id, paper_id, reason, summary
            ) VALUES (?, 'acquisition_attempted', 'acquisition_attempt', ?, ?, ?, ?)
            """,
            (
                attempted_at,
                str(attempt_id),
                paper_id,
                detail,
                f"{target_kind} via {route_family}/{resource_kind}: {outcome}",
            ),
        )
        connection.commit()

    return {
        "ok": True,
        "attempt": {
            "id": attempt_id,
            "candidate_id": candidate_id,
            "paper_id": paper_id,
            "target_kind": target_kind,
            "target_label": target_label,
            "route_family": route_family,
            "resource_kind": resource_kind,
            "source_url": source_url,
            "outcome": outcome,
            "detail": detail,
            "attempted_at": attempted_at,
        },
    }


def list_acquisition_attempts(
    project_root: Path,
    *,
    candidate_id: int | None = None,
    paper_id: str | None = None,
    target_kind: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise ResearchDbError("limit 必须在 1 到 500 之间。")
    where: list[str] = []
    params: list[Any] = []
    if candidate_id is not None:
        where.append("candidate_id = ?")
        params.append(candidate_id)
    if paper_id is not None:
        where.append("paper_id = ?")
        params.append(paper_id)
    if target_kind is not None:
        if target_kind not in TARGET_KINDS:
            raise ResearchDbError("target_kind 必须是：" + ", ".join(sorted(TARGET_KINDS)))
        where.append("target_kind = ?")
        params.append(target_kind)
    sql = "SELECT * FROM acquisition_attempts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY attempted_at, id LIMIT ?"
    params.append(limit)
    with connect(_db_path(project_root)) as connection:
        rows = [dict(row) for row in connection.execute(sql, params)]
    return {"ok": True, "attempts": rows}


def supplement_access_blockers(connection, paper_id: str, attempt_ids: list[int]) -> list[str]:
    if not attempt_ids:
        return ["supplement_attempt_ids_missing"]
    unique_ids = list(dict.fromkeys(attempt_ids))
    placeholders = ",".join("?" for _ in unique_ids)
    rows = connection.execute(
        f"SELECT id, route_family, resource_kind, source_url, outcome "
        f"FROM acquisition_attempts WHERE id IN ({placeholders}) "
        "AND paper_id = ? AND target_kind = 'supplement' ORDER BY id",
        (*unique_ids, paper_id),
    ).fetchall()
    blockers: list[str] = []
    if len(rows) != len(unique_ids):
        return ["supplement_attempt_reference_invalid"]
    if any(row["outcome"] == "acquired" for row in rows):
        blockers.append("supplement_attempt_refs_include_acquired")
    failed = [row for row in rows if row["outcome"] in FAILURE_OUTCOMES]
    if len(failed) < 2:
        blockers.append("supplement_attempts_insufficient")
        return blockers
    families = {str(row["route_family"]) for row in failed}
    publisher_resource_kinds = {
        str(row["resource_kind"])
        for row in failed
        if row["route_family"] == "publisher"
    }
    if len(families) < 2 and len(publisher_resource_kinds) < 2:
        blockers.append("supplement_alternate_route_missing")
    return blockers


def unavailable_candidate_blockers(connection, candidate) -> list[dict[str, Any]]:
    if candidate["acquisition_status"] != "unavailable":
        return []
    candidate_id = int(candidate["id"])
    attempts = connection.execute(
        """
        SELECT id, route_family, resource_kind, source_url, outcome
        FROM acquisition_attempts
        WHERE candidate_id = ? AND target_kind = 'main_text'
        ORDER BY id
        """,
        (candidate_id,),
    ).fetchall()
    blockers: list[dict[str, Any]] = []
    failed = [row for row in attempts if row["outcome"] in FAILURE_OUTCOMES]
    if len(failed) < 2:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_acquisition_attempts_insufficient",
                "attempt_count": len(failed),
            }
        )
        return blockers

    families = {str(row["route_family"]) for row in failed}
    if len(families) < 2:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_route_diversity_insufficient",
                "route_families": sorted(families),
            }
        )
    if candidate["doi"] and "publisher" not in families:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_missing_publisher_attempt",
            }
        )
    if not (families & {"open_index", "repository", "preprint"}):
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_missing_open_resolution_attempt",
            }
        )

    # A single blocked PDF endpoint is not evidence that the publisher has no full text.
    publisher_rows = [row for row in failed if row["route_family"] == "publisher"]
    blocked_pdf_only = publisher_rows and all(
        row["resource_kind"] == "pdf"
        and row["outcome"] in {"access_denied", "challenge", "invalid_artifact"}
        for row in publisher_rows
    )
    if blocked_pdf_only:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "publisher_pdf_failure_without_article_page_resolution",
            }
        )
    return blockers
