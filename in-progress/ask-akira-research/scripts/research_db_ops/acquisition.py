from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect
import research_db_ops.common as common


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
ACCESS_BASES = {
    "not_applicable",
    "publisher_open",
    "public_repository",
    "institutional_repository",
    "author_manuscript",
    "preprint",
    "authenticated_user",
    "user_provided",
    "unverified",
}
ADMISSIBLE_ACQUIRED_BASES = ACCESS_BASES - {"not_applicable", "unverified"}


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


def _int_list(value: object, *, field: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ResearchDbError(f"{field} 必须是整数数组。")
    result: list[int] = []
    for item in value:
        parsed = _optional_int(item, field=field)
        assert parsed is not None
        if parsed not in result:
            result.append(parsed)
    return result


@dataclass(frozen=True)
class _AttemptSpec:
    candidate_id: int | None
    paper_id: str | None
    target_kind: str
    target_label: str | None
    route_family: str
    resource_kind: str
    source_url: str
    outcome: str
    detail: str
    attempted_at: str
    access_basis: str
    access_basis_detail: str | None
    supersedes_attempt_ids: list[int]
    supersession_reason: str | None


def _parse_attempt(bundle: dict[str, Any]) -> _AttemptSpec:
    candidate_id = _optional_int(bundle.get("candidate_id"), field="candidate_id")
    paper_id = common.text(bundle.get("paper_id"))
    if candidate_id is None and paper_id is None:
        raise ResearchDbError("Acquisition Attempt 必须至少关联 candidate_id 或 paper_id。")

    target_kind = common.enum_value(bundle.get("target_kind"), TARGET_KINDS, default="main_text", field="target_kind")
    route_family = common.enum_value(bundle.get("route_family"), ROUTE_FAMILIES, default="other", field="route_family")
    resource_kind = common.enum_value(bundle.get("resource_kind"), RESOURCE_KINDS, default="other", field="resource_kind")
    outcome = common.enum_value(bundle.get("outcome"), OUTCOMES, default="other_failure", field="outcome")
    target_label = common.text(bundle.get("target_label"))
    source_url = common.text(bundle.get("source_url"), required=True, field="source_url")
    detail = common.text(bundle.get("detail"), required=True, field="detail")
    inferred_basis: str | None = None
    if outcome == "acquired" and bundle.get("access_basis") is None:
        if route_family == "publisher":
            inferred_basis = "publisher_open"
        elif route_family == "repository":
            inferred_basis = "public_repository"
        elif route_family == "preprint":
            inferred_basis = "preprint"
        elif route_family == "authenticated":
            inferred_basis = "authenticated_user"
        elif route_family == "open_index" and source_url and any(
            marker in source_url.casefold()
            for marker in ("pmc.ncbi.nlm.nih.gov/", "europepmc.org/", "ncbi.nlm.nih.gov/pmc/")
        ):
            inferred_basis = "public_repository"
    access_basis = common.enum_value(
        bundle.get("access_basis") if bundle.get("access_basis") is not None else inferred_basis,
        ACCESS_BASES,
        default="not_applicable" if outcome != "acquired" else "unverified",
        field="access_basis",
    )
    access_basis_detail = common.text(bundle.get("access_basis_detail"))
    if access_basis_detail is None and inferred_basis is not None:
        access_basis_detail = (
            f"Access basis inferred from acquisition route {route_family} and source URL {source_url}."
        )
    attempted_at = common.text(bundle.get("attempted_at")) or common.now()
    supersedes_attempt_ids = _int_list(
        bundle.get("supersedes_attempt_ids"), field="supersedes_attempt_ids"
    )
    supersession_reason = common.text(bundle.get("supersession_reason"))
    if supersedes_attempt_ids and not supersession_reason:
        raise ResearchDbError(
            "supersedes_attempt_ids 非空时必须提供 supersession_reason，说明为什么旧 attempt 判断失效。"
        )
    assert source_url is not None and detail is not None

    if target_kind != "main_text" and paper_id is None:
        raise ResearchDbError(f"target_kind={target_kind} 的 Acquisition Attempt 必须关联 paper_id。")
    if target_kind in {"supplement", "code_data"} and target_label is None:
        raise ResearchDbError(
            f"{target_kind} Acquisition Attempt 必须提供 target_label，明确具体附件、数据集或代码资源。"
        )
    if outcome == "acquired":
        if access_basis not in ADMISSIBLE_ACQUIRED_BASES:
            raise ResearchDbError(
                "outcome=acquired 必须提供可审计的 access_basis；来源依据不明的网络镜像不能闭合为正式全文。"
            )
        if not access_basis_detail:
            raise ResearchDbError(
                "outcome=acquired 必须提供 access_basis_detail，说明开放、授权或用户提供依据。"
            )
    elif access_basis != "not_applicable":
        raise ResearchDbError("非 acquired Acquisition Attempt 的 access_basis 必须为 not_applicable。")

    return _AttemptSpec(
        candidate_id=candidate_id,
        paper_id=paper_id,
        target_kind=target_kind,
        target_label=target_label,
        route_family=route_family,
        resource_kind=resource_kind,
        source_url=source_url,
        outcome=outcome,
        detail=detail,
        attempted_at=attempted_at,
        access_basis=access_basis,
        access_basis_detail=access_basis_detail,
        supersedes_attempt_ids=supersedes_attempt_ids,
        supersession_reason=supersession_reason,
    )


def _validate_attempt_entities(connection, spec: _AttemptSpec) -> None:
    if spec.candidate_id is not None:
        candidate = connection.execute(
            "SELECT id, paper_id, user_access_status, user_access_reason "
            "FROM candidates WHERE id = ?",
            (spec.candidate_id,),
        ).fetchone()
        if candidate is None:
            raise ResearchDbError(f"Candidate 不存在：{spec.candidate_id}")
        if spec.paper_id is not None and candidate["paper_id"] not in {None, spec.paper_id}:
            raise ResearchDbError(
                f"Candidate {spec.candidate_id} 已关联 {candidate['paper_id']}，与 attempt.paper_id={spec.paper_id} 不一致。"
            )
    if spec.paper_id is not None:
        paper = connection.execute("SELECT id FROM papers WHERE id = ?", (spec.paper_id,)).fetchone()
        if paper is None:
            raise ResearchDbError(f"Paper 不存在：{spec.paper_id}")


def _resolve_superseded_attempts(connection, spec: _AttemptSpec) -> list[Any]:
    superseded_rows = []
    for old_id in spec.supersedes_attempt_ids:
        old = connection.execute(
            "SELECT * FROM acquisition_attempts WHERE id = ?", (old_id,)
        ).fetchone()
        if old is None:
            raise ResearchDbError(f"被 supersede 的 Acquisition Attempt 不存在：{old_id}")
        if old["validity_status"] != "active":
            raise ResearchDbError(f"Acquisition Attempt {old_id} 已非 active，不能重复 supersede。")
        if old["target_kind"] != spec.target_kind:
            raise ResearchDbError(
                f"Acquisition Attempt {old_id} 的 target_kind 与新 attempt 不一致。"
            )
        if spec.candidate_id is not None and old["candidate_id"] != spec.candidate_id:
            raise ResearchDbError(
                f"Acquisition Attempt {old_id} 不属于 Candidate {spec.candidate_id}。"
            )
        if spec.paper_id is not None and old["paper_id"] != spec.paper_id:
            raise ResearchDbError(
                f"Acquisition Attempt {old_id} 不属于 Paper {spec.paper_id}。"
            )
        superseded_rows.append(old)
    return superseded_rows


def _insert_attempt(connection, spec: _AttemptSpec) -> int:
    cursor = connection.execute(
        """
        INSERT INTO acquisition_attempts(
            candidate_id, paper_id, target_kind, target_label, route_family,
            resource_kind, source_url, outcome, detail, attempted_at,
            access_basis, access_basis_detail
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            spec.candidate_id,
            spec.paper_id,
            spec.target_kind,
            spec.target_label,
            spec.route_family,
            spec.resource_kind,
            spec.source_url,
            spec.outcome,
            spec.detail,
            spec.attempted_at,
            spec.access_basis,
            spec.access_basis_detail,
        ),
    )
    return int(cursor.lastrowid)


def _update_user_access(connection, spec: _AttemptSpec) -> None:
    if (
        spec.candidate_id is not None
        and spec.target_kind == "main_text"
        and spec.outcome == "auth_required"
    ):
        connection.execute(
            """
            UPDATE candidates
            SET user_access_status = 'required',
                user_access_reason = ?,
                updated_at = ?
            WHERE id = ? AND acquisition_status <> 'acquired'
            """,
            (spec.detail, spec.attempted_at, spec.candidate_id),
        )


def _apply_supersession(connection, attempt_id: int, superseded_rows: list[Any], spec: _AttemptSpec) -> None:
    if superseded_rows:
        connection.executemany(
            """
            UPDATE acquisition_attempts
            SET validity_status = 'superseded',
                superseded_by_attempt_id = ?,
                supersession_reason = ?
            WHERE id = ?
            """,
            [
                (attempt_id, spec.supersession_reason, int(row["id"]))
                for row in superseded_rows
            ],
        )


def _write_attempt_change(connection, attempt_id: int, spec: _AttemptSpec) -> None:
    connection.execute(
        """
        INSERT INTO change_log(
            timestamp, action, entity_type, entity_id, paper_id, reason, summary
        ) VALUES (?, 'acquisition_attempted', 'acquisition_attempt', ?, ?, ?, ?)
        """,
        (
            spec.attempted_at,
            str(attempt_id),
            spec.paper_id,
            spec.supersession_reason or spec.detail,
            f"{spec.target_kind} via {spec.route_family}/{spec.resource_kind}: {spec.outcome}; "
            f"supersedes={spec.supersedes_attempt_ids or 'none'}",
        ),
    )


def record_acquisition_attempt(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    spec = _parse_attempt(bundle)
    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _validate_attempt_entities(connection, spec)
            superseded_rows = _resolve_superseded_attempts(connection, spec)
            attempt_id = _insert_attempt(connection, spec)
            _update_user_access(connection, spec)
            _apply_supersession(connection, attempt_id, superseded_rows, spec)
            _write_attempt_change(connection, attempt_id, spec)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "attempt": {
            "id": attempt_id,
            "candidate_id": spec.candidate_id,
            "paper_id": spec.paper_id,
            "target_kind": spec.target_kind,
            "target_label": spec.target_label,
            "route_family": spec.route_family,
            "resource_kind": spec.resource_kind,
            "source_url": spec.source_url,
            "outcome": spec.outcome,
            "detail": spec.detail,
            "attempted_at": spec.attempted_at,
            "access_basis": spec.access_basis,
            "access_basis_detail": spec.access_basis_detail,
            "validity_status": "active",
            "supersedes_attempt_ids": spec.supersedes_attempt_ids,
            "supersession_reason": spec.supersession_reason,
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
    with connect(common.db_path(project_root)) as connection:
        rows = [dict(row) for row in connection.execute(sql, params)]
    return {"ok": True, "attempts": rows}


def _main_text_access_blockers(
    connection,
    *,
    where_field: str,
    where_value: object,
    identity_field: str,
    missing_reason: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT id, route_family, source_url, outcome, validity_status,
               access_basis, access_basis_detail
        FROM acquisition_attempts
        WHERE {where_field} = ? AND target_kind = 'main_text'
        ORDER BY id
        """,
        (where_value,),
    ).fetchall()
    active_acquired = [
        row
        for row in rows
        if row["validity_status"] == "active" and row["outcome"] == "acquired"
    ]
    identity = {identity_field: where_value}
    if not active_acquired:
        return [{**identity, "reason": missing_reason}]

    blockers: list[dict[str, Any]] = []
    unverified = [
        row
        for row in active_acquired
        if str(row["access_basis"]) not in ADMISSIBLE_ACQUIRED_BASES
    ]
    if unverified:
        blockers.append(
            {
                **identity,
                "reason": "acquired_main_text_access_basis_unverified",
                "attempt_ids": [int(row["id"]) for row in unverified],
            }
        )
    missing_detail = [
        row
        for row in active_acquired
        if not (row["access_basis_detail"] and str(row["access_basis_detail"]).strip())
    ]
    if missing_detail:
        blockers.append(
            {
                **identity,
                "reason": "acquired_main_text_access_basis_detail_missing",
                "attempt_ids": [int(row["id"]) for row in missing_detail],
            }
        )
    return blockers


def acquired_main_text_access_blockers(connection, candidate_id: int) -> list[dict[str, Any]]:
    return _main_text_access_blockers(
        connection,
        where_field="candidate_id",
        where_value=candidate_id,
        identity_field="candidate_id",
        missing_reason="acquired_candidate_missing_main_text_access_attempt",
    )


def acquired_paper_main_text_access_blockers(connection, paper_id: str) -> list[dict[str, Any]]:
    return _main_text_access_blockers(
        connection,
        where_field="paper_id",
        where_value=paper_id,
        identity_field="paper_id",
        missing_reason="acquired_paper_missing_main_text_access_attempt",
    )


def supplement_access_blockers(connection, paper_id: str, attempt_ids: list[int]) -> list[str]:
    if not attempt_ids:
        return ["supplement_attempt_ids_missing"]
    unique_ids = list(dict.fromkeys(attempt_ids))
    placeholders = ",".join("?" for _ in unique_ids)
    rows = connection.execute(
        f"SELECT id, route_family, resource_kind, source_url, outcome, validity_status "
        f"FROM acquisition_attempts WHERE id IN ({placeholders}) "
        "AND paper_id = ? AND target_kind = 'supplement' ORDER BY id",
        (*unique_ids, paper_id),
    ).fetchall()
    blockers: list[str] = []
    if len(rows) != len(unique_ids):
        return ["supplement_attempt_reference_invalid"]
    if any(row["validity_status"] != "active" for row in rows):
        blockers.append("supplement_attempt_refs_include_superseded")
    if any(row["outcome"] == "acquired" for row in rows):
        blockers.append("supplement_attempt_refs_include_acquired")
    failed = [
        row for row in rows
        if row["validity_status"] == "active" and row["outcome"] in FAILURE_OUTCOMES
    ]
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


def code_data_access_blockers(
    connection,
    paper_id: str,
    attempt_ids: list[int],
    *,
    status: str,
) -> list[str]:
    if not attempt_ids:
        return ["code_data_attempt_ids_missing"]
    unique_ids = list(dict.fromkeys(attempt_ids))
    placeholders = ",".join("?" for _ in unique_ids)
    rows = connection.execute(
        f"SELECT id, route_family, resource_kind, source_url, outcome, validity_status "
        f"FROM acquisition_attempts WHERE id IN ({placeholders}) "
        "AND paper_id = ? AND target_kind = 'code_data' ORDER BY id",
        (*unique_ids, paper_id),
    ).fetchall()
    if len(rows) != len(unique_ids):
        return ["code_data_attempt_reference_invalid"]
    blockers: list[str] = []
    if any(row["validity_status"] != "active" for row in rows):
        blockers.append("code_data_attempt_refs_include_superseded")
    active = [row for row in rows if row["validity_status"] == "active"]
    if status == "checked":
        if not any(row["outcome"] == "acquired" for row in active):
            blockers.append("code_data_checked_without_acquired_attempt")
        return blockers

    failed = [row for row in active if row["outcome"] in FAILURE_OUTCOMES]
    if len(failed) < 2:
        blockers.append("code_data_attempts_insufficient")
        return blockers
    families = {str(row["route_family"]) for row in failed}
    resource_kinds = {str(row["resource_kind"]) for row in failed}
    if len(families) < 2 and len(resource_kinds) < 2:
        blockers.append("code_data_alternate_route_missing")
    return blockers


def unavailable_candidate_blockers(connection, candidate) -> list[dict[str, Any]]:
    if candidate["acquisition_status"] != "unavailable":
        return []
    candidate_id = int(candidate["id"])
    attempts = connection.execute(
        """
        SELECT id, route_family, resource_kind, source_url, outcome, validity_status
        FROM acquisition_attempts
        WHERE candidate_id = ? AND target_kind = 'main_text'
        ORDER BY id
        """,
        (candidate_id,),
    ).fetchall()
    blockers: list[dict[str, Any]] = []
    user_access_status = str(candidate["user_access_status"] or "not_required")
    user_access_reason = candidate["user_access_reason"]
    if user_access_status == "required":
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_waiting_for_user_access",
            }
        )
    if (
        str(candidate["reading_priority"]) in {"core", "high"}
        and user_access_status == "not_required"
    ):
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "priority_candidate_user_assistance_not_attempted",
            }
        )
    if user_access_status != "not_required" and not (
        user_access_reason and str(user_access_reason).strip()
    ):
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "user_access_reason_missing",
            }
        )

    active = [row for row in attempts if row["validity_status"] == "active"]
    active_acquired = [row for row in active if row["outcome"] == "acquired"]
    active_auth_required = [row for row in active if row["outcome"] == "auth_required"]
    if active_auth_required and user_access_status not in {
        "completed",
        "declined",
        "unavailable_to_user",
    }:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "authenticated_route_requires_user_resolution",
                "attempt_ids": [int(row["id"]) for row in active_auth_required],
            }
        )
    if active_acquired:
        blockers.append(
            {
                "candidate_id": candidate_id,
                "reason": "unavailable_has_active_acquired_attempt",
                "attempt_ids": [int(row["id"]) for row in active_acquired],
            }
        )
    failed = [row for row in active if row["outcome"] in FAILURE_OUTCOMES]
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
