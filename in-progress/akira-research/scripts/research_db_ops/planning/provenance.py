from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect
import research_db_ops.common as common


HYPOTHESIS_PROPOSAL_ORIGINS = {"user", "agent"}
USER_HYPOTHESIS_DECISIONS = {
    "accepted_for_exploration",
    "prioritized",
    "deferred",
    "rejected",
    "modified",
}
RESEARCH_JUDGMENT_ACTORS = {"user", "agent"}
RESEARCH_JUDGMENT_TYPES = {
    "scientific_assessment",
    "research_priority",
    "strategic_preference",
    "resource_constraint",
    "recommendation",
}


def _has_table(connection: Any, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        is not None
    )


def record_hypothesis_proposal(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"), field="proposal slug")
    origin = common.enum_value(
        bundle.get("origin"), HYPOTHESIS_PROPOSAL_ORIGINS, default="agent", field="origin"
    )
    original_statement = common.text(
        bundle.get("original_statement"), required=True, field="original_statement"
    )
    operationalized_statement = common.text(bundle.get("operationalized_statement"))
    operationalized_by = common.text(bundle.get("operationalized_by"))
    if operationalized_by is not None and operationalized_by not in HYPOTHESIS_PROPOSAL_ORIGINS:
        raise ResearchDbError("operationalized_by 必须是：agent, user")
    if (operationalized_statement is None) != (operationalized_by is None):
        raise ResearchDbError(
            "operationalized_statement 与 operationalized_by 必须同时提供或同时省略。"
        )
    rationale = common.text(bundle.get("rationale"))
    source_context = common.text(bundle.get("source_context"))
    if origin == "agent" and not rationale:
        raise ResearchDbError("Agent 提出的 Hypothesis Proposal 必须记录 rationale/evidence basis。")
    assert original_statement is not None

    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "hypothesis_proposals"):
            raise ResearchDbError("当前 research.sqlite 尚未支持 Hypothesis Proposal provenance；先运行 migrate。")
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT * FROM hypothesis_proposals WHERE slug = ?", (slug,)
            ).fetchone()
            source_values = {
                "origin": origin,
                "original_statement": original_statement,
                "rationale": rationale,
                "source_context": source_context,
            }
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO hypothesis_proposals(
                        slug, origin, original_statement, operationalized_statement,
                        operationalized_by, rationale, source_context, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        origin,
                        original_statement,
                        operationalized_statement,
                        operationalized_by,
                        rationale,
                        source_context,
                        now,
                    ),
                )
                proposal_id = int(cursor.lastrowid)
                connection.execute(
                    """
                    INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                    VALUES (?, 'hypothesis_proposal_recorded', 'hypothesis_proposal', ?, ?, ?)
                    """,
                    (
                        now,
                        str(proposal_id),
                        f"Hypothesis Proposal recorded with origin={origin}.",
                        f"proposal={slug}; origin={origin}",
                    ),
                )
            else:
                proposal_id = int(existing["id"])
                changed_source = [
                    field
                    for field, value in source_values.items()
                    if (existing[field] if existing[field] is not None else None) != value
                ]
                if changed_source:
                    raise ResearchDbError(
                        "Hypothesis Proposal 的来源字段不可覆盖；科学语义实质改变时请建立新 proposal："
                        + ", ".join(changed_source)
                    )

                existing_operationalized = (
                    str(existing["operationalized_statement"])
                    if existing["operationalized_statement"] is not None
                    else None
                )
                existing_operationalized_by = (
                    str(existing["operationalized_by"])
                    if existing["operationalized_by"] is not None
                    else None
                )
                if existing_operationalized is None and operationalized_statement is not None:
                    connection.execute(
                        """
                        UPDATE hypothesis_proposals
                        SET operationalized_statement = ?, operationalized_by = ?
                        WHERE id = ?
                        """,
                        (operationalized_statement, operationalized_by, proposal_id),
                    )
                    connection.execute(
                        """
                        INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                        VALUES (?, 'hypothesis_proposal_operationalized', 'hypothesis_proposal', ?, ?, ?)
                        """,
                        (
                            now,
                            str(proposal_id),
                            "Existing proposal was translated into an explicit testable formulation without changing its origin.",
                            f"proposal={slug}; operationalized_by={operationalized_by}",
                        ),
                    )
                elif existing_operationalized is not None:
                    if operationalized_statement is None:
                        operationalized_statement = existing_operationalized
                        operationalized_by = existing_operationalized_by
                    elif (
                        operationalized_statement != existing_operationalized
                        or operationalized_by != existing_operationalized_by
                    ):
                        raise ResearchDbError(
                            "Hypothesis Proposal 已有操作化表述；不能覆盖，科学语义实质改变时请建立新 proposal。"
                        )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"ok": True, "proposal_id": proposal_id, "slug": slug, "origin": origin}


def list_hypothesis_proposals(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "hypothesis_proposals"):
            return {"ok": True, "schema_capable": False, "hypothesis_proposals": []}
        rows: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT * FROM hypothesis_proposals ORDER BY id LIMIT ?", (limit,)
        ):
            item = dict(row)
            proposal_id = int(row["id"])
            item["hypothesis_set_slugs"] = [
                str(link["slug"])
                for link in connection.execute(
                    """
                    SELECT h.slug
                    FROM hypothesis_set_proposals hp
                    JOIN hypothesis_sets h ON h.id = hp.hypothesis_set_id
                    WHERE hp.proposal_id = ?
                    ORDER BY hp.created_at, h.id
                    """,
                    (proposal_id,),
                )
            ]
            latest_decision = connection.execute(
                """
                SELECT d.*, rp.slug AS resulting_proposal_slug
                FROM user_hypothesis_decisions d
                LEFT JOIN hypothesis_proposals rp ON rp.id = d.resulting_proposal_id
                WHERE d.proposal_id = ?
                ORDER BY d.decided_at DESC, d.id DESC
                LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
            item["latest_user_decision"] = dict(latest_decision) if latest_decision else None
            rows.append(item)
    return {"ok": True, "schema_capable": True, "hypothesis_proposals": rows}


def record_user_hypothesis_decision(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    proposal_slug = common.slug(bundle.get("proposal_slug"), field="proposal_slug")
    decision = common.enum_value(
        bundle.get("decision"),
        USER_HYPOTHESIS_DECISIONS,
        default="accepted_for_exploration",
        field="decision",
    )
    source_statement = common.text(
        bundle.get("source_statement"), required=True, field="source_statement"
    )
    rationale = common.text(bundle.get("rationale"))
    resulting_slug_raw = common.text(bundle.get("resulting_proposal_slug"))
    resulting_proposal_slug = (
        common.slug(resulting_slug_raw, field="resulting_proposal_slug")
        if resulting_slug_raw is not None
        else None
    )
    now = common.now()
    decided_at = common.text(bundle.get("decided_at")) or now
    if common.parse_timestamp(decided_at, field="decided_at") > common.parse_timestamp(now, field="recorded_at"):
        raise ResearchDbError("decided_at 不能晚于当前记录时间。")
    assert source_statement is not None

    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "user_hypothesis_decisions"):
            raise ResearchDbError("当前 research.sqlite 尚未支持 User Hypothesis Decision provenance；先运行 migrate。")
        connection.execute("BEGIN IMMEDIATE")
        try:
            proposal = connection.execute(
                "SELECT id FROM hypothesis_proposals WHERE slug = ?", (proposal_slug,)
            ).fetchone()
            if proposal is None:
                raise ResearchDbError(f"Hypothesis Proposal 不存在：{proposal_slug}")
            proposal_id = int(proposal["id"])
            resulting_proposal_id = None
            if decision == "modified" and resulting_proposal_slug is None:
                raise ResearchDbError(
                    "decision=modified 时必须通过 resulting_proposal_slug 指向新的 Hypothesis Proposal。"
                )
            if decision != "modified" and resulting_proposal_slug is not None:
                raise ResearchDbError(
                    "只有 decision=modified 才能提供 resulting_proposal_slug。"
                )
            if resulting_proposal_slug is not None:
                resulting = connection.execute(
                    "SELECT id FROM hypothesis_proposals WHERE slug = ?",
                    (resulting_proposal_slug,),
                ).fetchone()
                if resulting is None:
                    raise ResearchDbError(
                        f"resulting_proposal_slug 不存在：{resulting_proposal_slug}"
                    )
                resulting_proposal_id = int(resulting["id"])
                if resulting_proposal_id == proposal_id:
                    raise ResearchDbError("resulting_proposal_slug 必须指向新的 proposal。")
            cursor = connection.execute(
                """
                INSERT INTO user_hypothesis_decisions(
                    proposal_id, decision, source_statement, rationale, resulting_proposal_id,
                    decided_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    decision,
                    source_statement,
                    rationale,
                    resulting_proposal_id,
                    decided_at,
                    now,
                ),
            )
            decision_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'user_hypothesis_decision_recorded', 'user_hypothesis_decision', ?, ?, ?)
                """,
                (
                    now,
                    str(decision_id),
                    source_statement,
                    f"proposal={proposal_slug}; decision={decision}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {
        "ok": True,
        "decision_id": decision_id,
        "proposal_slug": proposal_slug,
        "decision": decision,
        "resulting_proposal_slug": resulting_proposal_slug,
    }


def list_user_hypothesis_decisions(
    project_root: Path, *, proposal_slug: str | None = None, limit: int = 100
) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "user_hypothesis_decisions"):
            return {"ok": True, "schema_capable": False, "user_hypothesis_decisions": []}
        params: list[Any] = []
        where = ""
        if proposal_slug is not None:
            normalized = common.slug(proposal_slug, field="proposal_slug")
            where = "WHERE p.slug = ?"
            params.append(normalized)
        params.append(limit)
        rows = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT d.*, p.slug AS proposal_slug, rp.slug AS resulting_proposal_slug
                FROM user_hypothesis_decisions d
                JOIN hypothesis_proposals p ON p.id = d.proposal_id
                LEFT JOIN hypothesis_proposals rp ON rp.id = d.resulting_proposal_id
                {where}
                ORDER BY d.decided_at, d.id
                LIMIT ?
                """,
                params,
            )
        ]
    return {"ok": True, "schema_capable": True, "user_hypothesis_decisions": rows}


def record_research_judgment(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    actor = common.enum_value(
        bundle.get("actor"), RESEARCH_JUDGMENT_ACTORS, default="agent", field="actor"
    )
    judgment_type = common.enum_value(
        bundle.get("judgment_type"),
        RESEARCH_JUDGMENT_TYPES,
        default="scientific_assessment",
        field="judgment_type",
    )
    statement = common.text(bundle.get("statement"), required=True, field="statement")
    basis = common.text(bundle.get("basis"))
    source_statement = common.text(bundle.get("source_statement"))
    proposal_slug_raw = common.text(bundle.get("proposal_slug"))
    proposal_slug = (
        common.slug(proposal_slug_raw, field="proposal_slug")
        if proposal_slug_raw is not None
        else None
    )
    if actor == "agent" and not basis:
        raise ResearchDbError("Agent judgment 必须记录 basis，说明其证据或项目状态依据。")
    if actor == "user" and not source_statement:
        raise ResearchDbError("User judgment 必须保留 source_statement，不能只保存 Agent 的改写。")
    assert statement is not None

    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "research_judgments"):
            raise ResearchDbError("当前 research.sqlite 尚未支持 Research Judgment provenance；先运行 migrate。")
        connection.execute("BEGIN IMMEDIATE")
        try:
            proposal_id = None
            if proposal_slug is not None:
                proposal = connection.execute(
                    "SELECT id FROM hypothesis_proposals WHERE slug = ?", (proposal_slug,)
                ).fetchone()
                if proposal is None:
                    raise ResearchDbError(f"Hypothesis Proposal 不存在：{proposal_slug}")
                proposal_id = int(proposal["id"])
            cursor = connection.execute(
                """
                INSERT INTO research_judgments(
                    actor, judgment_type, statement, basis, source_statement,
                    proposal_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (actor, judgment_type, statement, basis, source_statement, proposal_id, now),
            )
            judgment_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'research_judgment_recorded', 'research_judgment', ?, ?, ?)
                """,
                (
                    now,
                    str(judgment_id),
                    basis or source_statement,
                    f"actor={actor}; type={judgment_type}; proposal={proposal_slug or 'none'}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {
        "ok": True,
        "judgment_id": judgment_id,
        "actor": actor,
        "judgment_type": judgment_type,
        "proposal_slug": proposal_slug,
    }


def list_research_judgments(
    project_root: Path,
    *,
    actor: str | None = None,
    judgment_type: str | None = None,
    proposal_slug: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        if not _has_table(connection, "research_judgments"):
            return {"ok": True, "schema_capable": False, "research_judgments": []}
        clauses: list[str] = []
        params: list[Any] = []
        if actor is not None:
            actor = common.enum_value(actor, RESEARCH_JUDGMENT_ACTORS, default="agent", field="actor")
            clauses.append("j.actor = ?")
            params.append(actor)
        if judgment_type is not None:
            judgment_type = common.enum_value(
                judgment_type,
                RESEARCH_JUDGMENT_TYPES,
                default="scientific_assessment",
                field="judgment_type",
            )
            clauses.append("j.judgment_type = ?")
            params.append(judgment_type)
        if proposal_slug is not None:
            proposal_slug = common.slug(proposal_slug, field="proposal_slug")
            clauses.append("p.slug = ?")
            params.append(proposal_slug)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        rows = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT j.*, p.slug AS proposal_slug
                FROM research_judgments j
                LEFT JOIN hypothesis_proposals p ON p.id = j.proposal_id
                {where}
                ORDER BY j.created_at, j.id
                LIMIT ?
                """,
                params,
            )
        ]
    return {"ok": True, "schema_capable": True, "research_judgments": rows}


