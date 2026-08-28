from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect
from research_db_ops.discovery import _db_path, _enum, _now, _text


HYPOTHESIS_STATUSES = {"draft", "frozen", "superseded", "closed"}
DESIGN_STATUSES = {"draft", "frozen", "execution_ready", "superseded"}
FEASIBILITY_STATUSES = {"unresolved", "ready"}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_HYPOTHESIS_ORDER = {"draft": 0, "frozen": 1, "closed": 2, "superseded": 2}
_DESIGN_ORDER = {"draft": 0, "frozen": 1, "execution_ready": 2, "superseded": 2}


def _slug(value: object, *, field: str = "slug") -> str:
    text = _text(value, required=True, field=field)
    assert text is not None
    if not _SLUG_RE.fullmatch(text):
        raise ResearchDbError(f"{field} 必须使用 lowercase kebab-case。")
    return text


def _local_file(project_root: Path, value: object, *, field: str) -> str:
    text = _text(value, required=True, field=field)
    assert text is not None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = project_root / path
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ResearchDbError(f"{field} 必须位于科研项目目录内：{resolved}") from exc
    if not resolved.is_file():
        raise ResearchDbError(f"{field} 指向的文件不存在：{relative.as_posix()}")
    return relative.as_posix()


def record_hypothesis_set(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(bundle.get("slug"))
    title = _text(bundle.get("title"), required=True, field="title")
    target_uncertainty = _text(
        bundle.get("target_uncertainty"), required=True, field="target_uncertainty"
    )
    artifact_path = _local_file(
        project_root, bundle.get("artifact_path"), field="hypothesis artifact_path"
    )
    status = _enum(
        bundle.get("status"), HYPOTHESIS_STATUSES, default="draft", field="hypothesis status"
    )
    freeze_commit = _text(bundle.get("freeze_commit"))
    if status == "frozen" and not freeze_commit:
        raise ResearchDbError("Hypothesis Set 进入 frozen 时必须记录 freeze_commit。")

    now = _now()
    with connect(_db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT * FROM hypothesis_sets WHERE slug = ?", (slug,)
            ).fetchone()
            if existing is None:
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

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'hypothesis_set_recorded', 'hypothesis_set', ?, ?, ?)
                """,
                (
                    now,
                    str(hypothesis_set_id),
                    f"Hypothesis Set state recorded as {status}.",
                    f"hypothesis_set={slug}; status={status}",
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
    }


def record_design(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(bundle.get("slug"))
    title = _text(bundle.get("title"), required=True, field="title")
    hypothesis_slug = _slug(bundle.get("hypothesis_set_slug"), field="hypothesis_set_slug")
    target_estimand = _text(bundle.get("target_estimand"), required=True, field="target_estimand")
    primary_outcome = _text(bundle.get("primary_outcome"), required=True, field="primary_outcome")
    experimental_unit = _text(
        bundle.get("experimental_unit"), required=True, field="experimental_unit"
    )
    artifact_path = _local_file(
        project_root, bundle.get("artifact_path"), field="design artifact_path"
    )
    status = _enum(bundle.get("status"), DESIGN_STATUSES, default="draft", field="design status")
    feasibility_status = _enum(
        bundle.get("feasibility_status"),
        FEASIBILITY_STATUSES,
        default="unresolved",
        field="feasibility_status",
    )
    feasibility_summary = _text(bundle.get("feasibility_summary"))
    freeze_commit = _text(bundle.get("freeze_commit"))
    if status in {"frozen", "execution_ready"} and not freeze_commit:
        raise ResearchDbError("Design 进入 frozen/execution_ready 时必须记录 freeze_commit。")
    if feasibility_status == "unresolved" and not feasibility_summary:
        raise ResearchDbError("feasibility_status=unresolved 时必须说明 feasibility_summary。")
    if status == "execution_ready" and feasibility_status != "ready":
        raise ResearchDbError("Design 只有在 feasibility_status=ready 时才能标记 execution_ready。")

    now = _now()
    with connect(_db_path(project_root)) as connection:
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
    with connect(_db_path(project_root)) as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM hypothesis_sets ORDER BY id LIMIT ?", (limit,)
            )
        ]
    return {"ok": True, "hypothesis_sets": rows}


def list_designs(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(_db_path(project_root)) as connection:
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
