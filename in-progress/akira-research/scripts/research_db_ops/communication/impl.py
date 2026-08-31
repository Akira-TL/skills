from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect
import research_db_ops.common as common


COMMUNICATION_STATUSES = {"draft", "completed", "superseded"}
COMMUNICATION_ROLES = {
    "title_abstract",
    "methods",
    "results",
    "discussion",
    "figure",
    "figure_legend",
    "table",
    "lay_summary",
    "traceability",
    "generator",
    "other",
}
COMMUNICATION_TIMING_ROLES = {"source_support", "derived_output"}


def record_communication(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    title = common.text(bundle.get("title"), required=True, field="title")
    purpose = common.text(bundle.get("purpose"), required=True, field="purpose")
    audience = common.text(bundle.get("audience"), required=True, field="audience")
    source_commit = common.text(bundle.get("source_commit"), required=True, field="source_commit")
    status = common.enum_value(bundle.get("status"), COMMUNICATION_STATUSES, default="draft", field="status")
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ResearchDbError("communication artifacts 必须是非空数组。")

    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(artifacts, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"communication artifact {index} 必须是 JSON object。")
        role = common.enum_value(item.get("role"), COMMUNICATION_ROLES, default="other", field="communication artifact role")
        path = common.local_path(project_root, item.get("path"), field="communication artifact path")
        timing_role = common.enum_value(
            item.get("timing_role"),
            COMMUNICATION_TIMING_ROLES,
            default="derived_output",
            field="communication artifact timing_role",
        )
        git_tracking = common.tracking(item.get("git_tracking"))
        tracking_reason = common.text(item.get("tracking_reason"))
        if git_tracking == "not_required" and not tracking_reason:
            raise ResearchDbError("communication artifact git_tracking=not_required 时必须说明 tracking_reason。")
        parsed.append(
            {
                "role": role,
                "path": path,
                "timing_role": timing_role,
                "git_tracking": git_tracking,
                "tracking_reason": tracking_reason,
            }
        )

    assert title is not None and purpose is not None and audience is not None and source_commit is not None
    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT * FROM communication_products WHERE slug = ?", (slug,)
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO communication_products(
                        slug, title, purpose, audience, source_commit, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (slug, title, purpose, audience, source_commit, status, now, now),
                )
                product_id = int(cursor.lastrowid)
            else:
                product_id = int(existing["id"])
                if existing["status"] == "completed":
                    immutable = ("title", "purpose", "audience", "source_commit")
                    changed = [
                        field
                        for field, value in zip(immutable, (title, purpose, audience, source_commit))
                        if str(existing[field]) != str(value)
                    ]
                    if changed:
                        raise ResearchDbError(
                            "completed Communication Product 不能静默修改来源或定义字段："
                            + ", ".join(changed)
                        )
                    if status != "completed":
                        raise ResearchDbError("completed Communication Product 不能回退状态。")
                if existing["status"] == "superseded":
                    raise ResearchDbError("superseded Communication Product 不能重新激活。")
                connection.execute(
                    """
                    UPDATE communication_products
                    SET title = ?, purpose = ?, audience = ?, source_commit = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (title, purpose, audience, source_commit, status, now, product_id),
                )

            for item in parsed:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO communication_artifacts(
                        product_id, role, path, timing_role, git_tracking, tracking_reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id,
                        item["role"],
                        item["path"],
                        item["timing_role"],
                        item["git_tracking"],
                        item["tracking_reason"],
                        now,
                    ),
                )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'communication_recorded', 'communication_product', ?, ?, ?)
                """,
                (
                    now,
                    str(product_id),
                    f"Communication Product state recorded as {status}.",
                    f"communication={slug}; status={status}; artifacts={len(parsed)}; source_commit={source_commit}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"ok": True, "communication_id": product_id, "slug": slug, "status": status}


def list_communications(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        rows: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT * FROM communication_products ORDER BY id LIMIT ?", (limit,)
        ):
            item = dict(row)
            item["artifacts"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM communication_artifacts WHERE product_id = ? ORDER BY id",
                    (row["id"],),
                )
            ]
            rows.append(item)
    return {"ok": True, "communications": rows}
