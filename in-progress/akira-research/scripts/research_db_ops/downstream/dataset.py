from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError, connect
import research_db_ops.common as common


DATASET_ROLES = {"raw", "curated", "metadata", "manifest", "other"}
STORAGE_KINDS = {"local", "external"}

def record_dataset(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    title = common.text(bundle.get("title"), required=True, field="title")
    source = common.text(bundle.get("source"), required=True, field="source")
    received_at = common.text(bundle.get("received_at"), required=True, field="received_at")
    unit = common.text(bundle.get("unit_of_inference"), required=True, field="unit_of_inference")
    provenance_path = common.local_path(project_root, bundle.get("provenance_path"), field="provenance_path")
    identity = common.text(bundle.get("identity"))
    source_url = common.text(bundle.get("source_url"))
    version = common.text(bundle.get("version"))
    status = common.enum_value(bundle.get("status"), {"active", "archived"}, default="active", field="status")
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ResearchDbError("dataset artifacts 必须是非空数组。")

    parsed_artifacts: list[dict[str, Any]] = []
    for index, item in enumerate(artifacts, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"dataset artifact {index} 必须是 JSON object。")
        role = common.enum_value(item.get("role"), DATASET_ROLES, default="other", field="dataset artifact role")
        storage_kind = common.enum_value(
            item.get("storage_kind"), STORAGE_KINDS, default="local", field="storage_kind"
        )
        git_tracking = common.tracking(item.get("git_tracking"))
        tracking_reason = common.text(item.get("tracking_reason"))
        if git_tracking == "not_required" and not tracking_reason:
            raise ResearchDbError("git_tracking=not_required 时必须说明 tracking_reason。")
        if storage_kind == "local":
            location = common.local_path(project_root, item.get("location"), field="dataset artifact location")
        else:
            location = common.text(item.get("location"), required=True, field="dataset artifact location")
            assert location is not None
            if git_tracking == "required":
                raise ResearchDbError("external dataset artifact 不能声明 git_tracking=required。")
        parsed_artifacts.append(
            {
                "role": role,
                "location": location,
                "storage_kind": storage_kind,
                "git_tracking": git_tracking,
                "tracking_reason": tracking_reason,
                "source_url": common.text(item.get("source_url")),
                "version": common.text(item.get("version")),
            }
        )

    now = common.now()
    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT * FROM datasets WHERE slug = ?", (slug,)
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO datasets(
                        slug, title, identity, source, source_url, version, received_at,
                        unit_of_inference, provenance_path, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        title,
                        identity,
                        source,
                        source_url,
                        version,
                        received_at,
                        unit,
                        provenance_path,
                        status,
                        now,
                        now,
                    ),
                )
                dataset_id = int(cursor.lastrowid)
            else:
                dataset_id = int(existing["id"])
                immutable = {
                    "title": title,
                    "identity": identity,
                    "source": source,
                    "source_url": source_url,
                    "version": version,
                    "received_at": received_at,
                    "unit_of_inference": unit,
                    "provenance_path": provenance_path,
                    "status": status,
                }
                changed = [
                    field
                    for field, value in immutable.items()
                    if (existing[field] if existing[field] is not None else None) != value
                ]
                if changed:
                    raise ResearchDbError(
                        "Dataset 已登记后不能通过 record-dataset 静默修改核心身份字段："
                        + ", ".join(changed)
                        + "。如数据版本/身份已改变，应建立新的 Dataset。"
                    )
            for item in parsed_artifacts:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO dataset_artifacts(
                        dataset_id, role, location, storage_kind, git_tracking,
                        tracking_reason, source_url, version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        item["role"],
                        item["location"],
                        item["storage_kind"],
                        item["git_tracking"],
                        item["tracking_reason"],
                        item["source_url"],
                        item["version"],
                        now,
                    ),
                )
            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'dataset_recorded', 'dataset', ?, ?, ?)
                """,
                (
                    now,
                    str(dataset_id),
                    "Dataset provenance entered canonical research state.",
                    f"dataset={slug}; artifacts={len(parsed_artifacts)}; unit={unit}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"ok": True, "dataset_id": dataset_id, "slug": slug}

def list_datasets(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        rows = []
        for row in connection.execute("SELECT * FROM datasets ORDER BY id LIMIT ?", (limit,)):
            item = dict(row)
            item["artifacts"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM dataset_artifacts WHERE dataset_id = ? ORDER BY id", (row["id"],)
                )
            ]
            rows.append(item)
    return {"ok": True, "datasets": rows}
