from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect
import research_db_ops.common as common


HYPOTHESIS_STATUSES = {"draft", "frozen", "superseded", "closed"}
DESIGN_STATUSES = {"draft", "frozen", "execution_ready", "superseded"}
FEASIBILITY_STATUSES = {"unresolved", "ready"}
HYPOTHESIS_RESOLUTION_STATUSES = {
    "unresolved",
    "partially_resolved",
    "resolved",
    "not_interpretable",
}
_HYPOTHESIS_ORDER = {"draft": 0, "frozen": 1, "closed": 2, "superseded": 2}
_DESIGN_ORDER = {"draft": 0, "frozen": 1, "execution_ready": 2, "superseded": 2}


def _slug_list(value: object, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ResearchDbError(f"{field} 必须是 JSON array。")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        slug = common.slug(item, field=field)
        if slug in seen:
            continue
        seen.add(slug)
        result.append(slug)
    return result


def _has_table(connection: Any, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        is not None
    )


def _proposal_ids(connection: Any, proposal_slugs: list[str]) -> dict[str, int]:
    if not proposal_slugs:
        return {}
    if not _has_table(connection, "hypothesis_proposals"):
        raise ResearchDbError("当前 research.sqlite 尚未支持 Hypothesis Proposal provenance；先运行 migrate。")
    rows = connection.execute(
        "SELECT id, slug FROM hypothesis_proposals WHERE slug IN ("
        + ",".join("?" for _ in proposal_slugs)
        + ")",
        proposal_slugs,
    ).fetchall()
    mapping = {str(row["slug"]): int(row["id"]) for row in rows}
    missing = [slug for slug in proposal_slugs if slug not in mapping]
    if missing:
        raise ResearchDbError("Hypothesis Set 引用了不存在的 proposal：" + ", ".join(missing))
    return mapping


def record_hypothesis_set(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    title = common.text(bundle.get("title"), required=True, field="title")
    target_uncertainty = common.text(
        bundle.get("target_uncertainty"), required=True, field="target_uncertainty"
    )
    artifact_path = common.local_path(
        project_root, bundle.get("artifact_path"), field="hypothesis artifact_path", require_file=True
    )
    status = common.enum_value(
        bundle.get("status"), HYPOTHESIS_STATUSES, default="draft", field="hypothesis status"
    )
    freeze_commit = common.text(bundle.get("freeze_commit"))
    proposal_slugs = _slug_list(bundle.get("proposal_slugs"), field="proposal_slugs")
    if status == "frozen" and not freeze_commit:
        raise ResearchDbError("Hypothesis Set 进入 frozen 时必须记录 freeze_commit。")

    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            proposal_schema = _has_table(connection, "hypothesis_proposals")
            proposal_mapping = _proposal_ids(connection, proposal_slugs) if proposal_slugs else {}
            existing = connection.execute(
                "SELECT * FROM hypothesis_sets WHERE slug = ?", (slug,)
            ).fetchone()
            if existing is None:
                if proposal_schema and not proposal_slugs:
                    raise ResearchDbError(
                        "新建 Hypothesis Set 必须通过 proposal_slugs 指回至少一个已记录的 Hypothesis Proposal。"
                    )
                cursor = connection.execute(
                    """
                    INSERT INTO hypothesis_sets(
                        slug, title, target_uncertainty, artifact_path, status,
                        freeze_commit, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        title,
                        target_uncertainty,
                        artifact_path,
                        status,
                        freeze_commit,
                        now,
                        now,
                    ),
                )
                hypothesis_set_id = int(cursor.lastrowid)
            else:
                hypothesis_set_id = int(existing["id"])
                if existing["status"] in {"frozen", "closed", "superseded"}:
                    changed = [
                        field
                        for field, value in {
                            "title": title,
                            "target_uncertainty": target_uncertainty,
                            "artifact_path": artifact_path,
                        }.items()
                        if str(existing[field]) != str(value)
                    ]
                    if changed:
                        raise ResearchDbError(
                            "Hypothesis Set 冻结后不能静默修改 canonical 字段："
                            + ", ".join(changed)
                            + "。需要显式建立新版本/新集合。"
                        )
                    if proposal_slugs and proposal_schema:
                        linked = {
                            str(row["slug"])
                            for row in connection.execute(
                                """
                                SELECT p.slug
                                FROM hypothesis_set_proposals hp
                                JOIN hypothesis_proposals p ON p.id = hp.proposal_id
                                WHERE hp.hypothesis_set_id = ?
                                """,
                                (hypothesis_set_id,),
                            )
                        }
                        new_links = [proposal for proposal in proposal_slugs if proposal not in linked]
                        if new_links:
                            raise ResearchDbError(
                                "Hypothesis Set 冻结后不能补写新的 proposal provenance："
                                + ", ".join(new_links)
                            )
                old_status = str(existing["status"])
                if old_status in {"closed", "superseded"} and status != old_status:
                    raise ResearchDbError(f"{old_status} Hypothesis Set 不能重新激活。")
                if _HYPOTHESIS_ORDER[status] < _HYPOTHESIS_ORDER[old_status]:
                    raise ResearchDbError("Hypothesis Set status 不能回退。")
                if old_status == "draft":
                    connection.execute(
                        """
                        UPDATE hypothesis_sets
                        SET title = ?, target_uncertainty = ?, artifact_path = ?, status = ?,
                            freeze_commit = COALESCE(?, freeze_commit), updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            title,
                            target_uncertainty,
                            artifact_path,
                            status,
                            freeze_commit,
                            now,
                            hypothesis_set_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE hypothesis_sets
                        SET status = ?, freeze_commit = COALESCE(?, freeze_commit), updated_at = ?
                        WHERE id = ?
                        """,
                        (status, freeze_commit, now, hypothesis_set_id),
                    )

            if proposal_schema:
                for proposal_slug in proposal_slugs:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO hypothesis_set_proposals(
                            hypothesis_set_id, proposal_id, created_at
                        ) VALUES (?, ?, ?)
                        """,
                        (hypothesis_set_id, proposal_mapping[proposal_slug], now),
                    )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'hypothesis_set_recorded', 'hypothesis_set', ?, ?, ?)
                """,
                (
                    now,
                    str(hypothesis_set_id),
                    f"Hypothesis Set state recorded as {status}.",
                    f"hypothesis_set={slug}; status={status}; proposals={','.join(proposal_slugs) or 'legacy/untracked'}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {
        "ok": True,
        "hypothesis_set_id": hypothesis_set_id,
        "slug": slug,
        "status": status,
        "proposal_slugs": proposal_slugs,
    }


def record_design(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    title = common.text(bundle.get("title"), required=True, field="title")
    hypothesis_slug = common.slug(bundle.get("hypothesis_set_slug"), field="hypothesis_set_slug")
    target_estimand = common.text(bundle.get("target_estimand"), required=True, field="target_estimand")
    primary_outcome = common.text(bundle.get("primary_outcome"), required=True, field="primary_outcome")
    experimental_unit = common.text(
        bundle.get("experimental_unit"), required=True, field="experimental_unit"
    )
    artifact_path = common.local_path(
        project_root, bundle.get("artifact_path"), field="design artifact_path", require_file=True
    )
    status = common.enum_value(bundle.get("status"), DESIGN_STATUSES, default="draft", field="design status")
    feasibility_status = common.enum_value(
        bundle.get("feasibility_status"),
        FEASIBILITY_STATUSES,
        default="unresolved",
        field="feasibility_status",
    )
    feasibility_summary = common.text(bundle.get("feasibility_summary"))
    freeze_commit = common.text(bundle.get("freeze_commit"))
    if status in {"frozen", "execution_ready"} and not freeze_commit:
        raise ResearchDbError("Design 进入 frozen/execution_ready 时必须记录 freeze_commit。")
    if feasibility_status == "unresolved" and not feasibility_summary:
        raise ResearchDbError("feasibility_status=unresolved 时必须说明 feasibility_summary。")
    if status == "execution_ready" and feasibility_status != "ready":
        raise ResearchDbError("Design 只有在 feasibility_status=ready 时才能标记 execution_ready。")

    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            hypothesis = connection.execute(
                "SELECT id, status, freeze_commit FROM hypothesis_sets WHERE slug = ?", (hypothesis_slug,)
            ).fetchone()
            if hypothesis is None:
                raise ResearchDbError(f"Design 引用不存在的 Hypothesis Set：{hypothesis_slug}")
            hypothesis_set_id = int(hypothesis["id"])
            if status in {"frozen", "execution_ready"}:
                if hypothesis["status"] == "draft":
                    raise ResearchDbError("Design 冻结前，关联 Hypothesis Set 必须先冻结或闭合。")
                if not (hypothesis["freeze_commit"] and str(hypothesis["freeze_commit"]).strip()):
                    raise ResearchDbError(
                        "Design 冻结前，关联 Hypothesis Set 必须已有可审计 freeze_commit；"
                        "不能只靠状态标签代替冻结 provenance。"
                    )

            existing = connection.execute(
                "SELECT * FROM research_designs WHERE slug = ?", (slug,)
            ).fetchone()
            immutable = {
                "title": title,
                "hypothesis_set_id": hypothesis_set_id,
                "target_estimand": target_estimand,
                "primary_outcome": primary_outcome,
                "experimental_unit": experimental_unit,
                "artifact_path": artifact_path,
            }
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO research_designs(
                        slug, title, hypothesis_set_id, target_estimand, primary_outcome,
                        experimental_unit, artifact_path, status, feasibility_status,
                        feasibility_summary, freeze_commit, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        title,
                        hypothesis_set_id,
                        target_estimand,
                        primary_outcome,
                        experimental_unit,
                        artifact_path,
                        status,
                        feasibility_status,
                        feasibility_summary,
                        freeze_commit,
                        now,
                        now,
                    ),
                )
                design_id = int(cursor.lastrowid)
            else:
                design_id = int(existing["id"])
                if existing["status"] in {"frozen", "execution_ready", "superseded"}:
                    changed = [
                        field for field, value in immutable.items() if str(existing[field]) != str(value)
                    ]
                    if changed:
                        raise ResearchDbError(
                            "Design 冻结后不能静默修改 canonical 字段："
                            + ", ".join(changed)
                            + "。需要显式建立新版本或 pre-data amendment。"
                        )
                old_status = str(existing["status"])
                if old_status == "superseded" and status != "superseded":
                    raise ResearchDbError("superseded Design 不能重新激活。")
                if _DESIGN_ORDER[status] < _DESIGN_ORDER[old_status]:
                    raise ResearchDbError("Design status 不能回退。")
                if old_status == "draft":
                    connection.execute(
                        """
                        UPDATE research_designs
                        SET title = ?, hypothesis_set_id = ?, target_estimand = ?,
                            primary_outcome = ?, experimental_unit = ?, artifact_path = ?,
                            status = ?, feasibility_status = ?, feasibility_summary = ?,
                            freeze_commit = COALESCE(?, freeze_commit), updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            title,
                            hypothesis_set_id,
                            target_estimand,
                            primary_outcome,
                            experimental_unit,
                            artifact_path,
                            status,
                            feasibility_status,
                            feasibility_summary,
                            freeze_commit,
                            now,
                            design_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE research_designs
                        SET status = ?, feasibility_status = ?, feasibility_summary = ?,
                            freeze_commit = COALESCE(?, freeze_commit), updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            status,
                            feasibility_status,
                            feasibility_summary,
                            freeze_commit,
                            now,
                            design_id,
                        ),
                    )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'design_recorded', 'research_design', ?, ?, ?)
                """,
                (
                    now,
                    str(design_id),
                    f"Research Design state recorded as {status}.",
                    f"design={slug}; hypothesis_set={hypothesis_slug}; status={status}; feasibility={feasibility_status}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"ok": True, "design_id": design_id, "slug": slug, "status": status}


def list_hypothesis_sets(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        proposal_schema = _has_table(connection, "hypothesis_set_proposals")
        rows: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT * FROM hypothesis_sets ORDER BY id LIMIT ?", (limit,)
        ):
            item = dict(row)
            item["proposal_slugs"] = (
                [
                    str(link["slug"])
                    for link in connection.execute(
                        """
                        SELECT p.slug
                        FROM hypothesis_set_proposals hp
                        JOIN hypothesis_proposals p ON p.id = hp.proposal_id
                        WHERE hp.hypothesis_set_id = ?
                        ORDER BY hp.created_at, p.id
                        """,
                        (int(row["id"]),),
                    )
                ]
                if proposal_schema
                else None
            )
            rows.append(item)
    return {
        "ok": True,
        "schema_capabilities": {"hypothesis_proposal_provenance": proposal_schema},
        "hypothesis_sets": rows,
    }


def list_designs(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        rows: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT d.*, h.slug AS hypothesis_set_slug
            FROM research_designs d
            JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
            ORDER BY d.id LIMIT ?
            """,
            (limit,),
        ):
            rows.append(dict(row))
    return {"ok": True, "designs": rows}


def record_hypothesis_evaluation(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    hypothesis_slug = common.slug(bundle.get("hypothesis_set_slug"), field="hypothesis_set_slug")
    analysis_slug = common.slug(bundle.get("analysis_slug"), field="analysis_slug")
    resolution_value = common.text(
        bundle.get("resolution_status"), required=True, field="resolution_status"
    )
    resolution_status = common.enum_value(
        resolution_value,
        HYPOTHESIS_RESOLUTION_STATUSES,
        default="unresolved",
        field="resolution_status",
    )
    decision = common.text(bundle.get("decision"), required=True, field="decision")
    summary = common.text(bundle.get("summary"), required=True, field="summary")
    source_path = common.local_path(
        project_root, bundle.get("source_path"), field="evaluation source_path", require_file=True
    )
    now = common.now()
    evaluated_at = common.text(bundle.get("evaluated_at")) or now
    evaluated_time = common.parse_timestamp(evaluated_at, field="evaluated_at")
    recorded_time = common.parse_timestamp(now, field="recorded_at")
    if evaluated_time > recorded_time:
        raise ResearchDbError("evaluated_at 不能晚于当前记录时间。")
    assert decision is not None and summary is not None

    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            hypothesis = connection.execute(
                "SELECT id FROM hypothesis_sets WHERE slug = ?", (hypothesis_slug,)
            ).fetchone()
            if hypothesis is None:
                raise ResearchDbError(f"Hypothesis Set 不存在：{hypothesis_slug}")
            analysis = connection.execute(
                "SELECT id, status, design_id, completed_at FROM analysis_runs WHERE slug = ?",
                (analysis_slug,),
            ).fetchone()
            if analysis is None:
                raise ResearchDbError(f"Analysis 不存在：{analysis_slug}")
            if analysis["status"] != "completed":
                raise ResearchDbError("Hypothesis Evaluation 只能引用 completed Analysis。")
            if analysis["completed_at"] is None:
                raise ResearchDbError("completed Analysis 缺少 completed_at，不能记录 Hypothesis Evaluation。")
            completed_time = common.parse_timestamp(
                analysis["completed_at"], field="Analysis completed_at"
            )
            if evaluated_time < completed_time:
                raise ResearchDbError(
                    "Hypothesis Evaluation 的 evaluated_at 不能早于 Analysis completed_at。"
                )

            hypothesis_set_id = int(hypothesis["id"])
            analysis_id = int(analysis["id"])
            source_artifact = connection.execute(
                "SELECT id FROM analysis_artifacts WHERE analysis_id = ? AND path = ?",
                (analysis_id, source_path),
            ).fetchone()
            if source_artifact is None:
                raise ResearchDbError(
                    "Hypothesis Evaluation 的 source_path 必须已登记为当前 Analysis artifact："
                    + source_path
                )
            source_artifact_id = int(source_artifact["id"])
            if analysis["design_id"] is not None:
                design = connection.execute(
                    "SELECT hypothesis_set_id FROM research_designs WHERE id = ?",
                    (int(analysis["design_id"]),),
                ).fetchone()
                if design is None or int(design["hypothesis_set_id"]) != hypothesis_set_id:
                    raise ResearchDbError(
                        "Hypothesis Evaluation 与 Analysis 所实现 Design 的 Hypothesis Set 不一致。"
                    )

            if connection.execute(
                "SELECT 1 FROM hypothesis_evaluations WHERE hypothesis_set_id = ? AND analysis_id = ?",
                (hypothesis_set_id, analysis_id),
            ).fetchone():
                raise ResearchDbError(
                    "同一 Hypothesis Set 与 Analysis 已存在 Evaluation；科研评价事件不可覆盖。"
                )

            cursor = connection.execute(
                """
                INSERT INTO hypothesis_evaluations(
                    hypothesis_set_id, analysis_id, source_artifact_id, resolution_status,
                    decision, summary, evaluated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis_set_id,
                    analysis_id,
                    source_artifact_id,
                    resolution_status,
                    decision,
                    summary,
                    evaluated_at,
                    now,
                ),
            )
            evaluation_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'hypothesis_evaluated', 'hypothesis_evaluation', ?, ?, ?)
                """,
                (
                    now,
                    str(evaluation_id),
                    summary,
                    f"hypothesis_set={hypothesis_slug}; analysis={analysis_slug}; "
                    f"resolution={resolution_status}; decision={decision}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "hypothesis_evaluation_id": evaluation_id,
        "hypothesis_set_slug": hypothesis_slug,
        "analysis_slug": analysis_slug,
        "resolution_status": resolution_status,
        "decision": decision,
    }


def list_hypothesis_evaluations(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.*, h.slug AS hypothesis_set_slug, a.slug AS analysis_slug
                FROM hypothesis_evaluations e
                JOIN hypothesis_sets h ON h.id = e.hypothesis_set_id
                JOIN analysis_runs a ON a.id = e.analysis_id
                ORDER BY e.id LIMIT ?
                """,
                (limit,),
            )
        ]
    return {"ok": True, "hypothesis_evaluations": rows}
