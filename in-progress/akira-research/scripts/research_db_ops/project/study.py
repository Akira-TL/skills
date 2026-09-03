from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError, connect


STUDY_STATUSES = {"in_progress", "completed", "aborted"}
SAMPLE_STATUSES = {"collected", "failed", "missing", "archived"}
ASSAY_STATUSES = {"started", "completed", "failed"}
STUDY_ARTIFACT_ROLES = {
    "protocol",
    "sample_manifest",
    "assay_metadata",
    "deviation_log",
    "execution_log",
    "other",
}
STORAGE_KINDS = {"local", "external"}
_STUDY_TRANSITIONS = {
    "in_progress": {"in_progress", "completed", "aborted"},
    "completed": {"completed"},
    "aborted": {"aborted"},
}
_SAMPLE_TRANSITIONS = {
    "collected": {"collected", "archived"},
    "failed": {"failed", "archived"},
    "missing": {"missing", "archived"},
    "archived": {"archived"},
}
_ASSAY_TRANSITIONS = {
    "started": {"started", "completed", "failed"},
    "completed": {"completed"},
    "failed": {"failed"},
}


def _metadata_json(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ResearchDbError(f"{field} 必须是 JSON object。")
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _study_by_slug(connection: Any, slug: str) -> Any:
    row = connection.execute("SELECT * FROM studies WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ResearchDbError(f"Study 不存在：{slug}")
    return row


def _record_samples(connection: Any, study_id: int, items: object, now: str) -> dict[str, int]:
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ResearchDbError("samples 必须是 JSON array。")

    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"sample {index} 必须是 JSON object。")
        sample_key = common.text(item.get("sample_key"), required=True, field="sample_key")
        assert sample_key is not None
        parsed.append(
            {
                "sample_key": sample_key,
                "source_identity": common.text(item.get("source_identity")),
                "experimental_unit_identity": common.text(item.get("experimental_unit_identity")),
                "parent_sample_key": common.text(item.get("parent_sample_key")),
                "sample_type": common.text(item.get("sample_type")),
                "status": common.enum_value(
                    item.get("status"), SAMPLE_STATUSES, default="collected", field="sample status"
                ),
                "metadata_json": _metadata_json(item.get("metadata"), field="sample metadata"),
            }
        )

    sample_ids: dict[str, int] = {}
    for item in parsed:
        existing = connection.execute(
            "SELECT * FROM study_samples WHERE study_id = ? AND sample_key = ?",
            (study_id, item["sample_key"]),
        ).fetchone()
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO study_samples(
                    study_id, sample_key, source_identity, experimental_unit_identity,
                    parent_sample_id, sample_type, status, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    item["sample_key"],
                    item["source_identity"],
                    item["experimental_unit_identity"],
                    item["sample_type"],
                    item["status"],
                    item["metadata_json"],
                    now,
                ),
            )
            sample_id = int(cursor.lastrowid)
        else:
            sample_id = int(existing["id"])
            immutable = {
                "source_identity": item["source_identity"],
                "experimental_unit_identity": item["experimental_unit_identity"],
                "sample_type": item["sample_type"],
                "metadata_json": item["metadata_json"],
            }
            changed = [
                field
                for field, value in immutable.items()
                if (existing[field] if existing[field] is not None else None) != value
            ]
            if changed:
                raise ResearchDbError(
                    f"Sample {item['sample_key']} 的 identity/metadata 不可静默改写："
                    + ", ".join(changed)
                )
            old_status = str(existing["status"])
            if item["status"] not in _SAMPLE_TRANSITIONS[old_status]:
                raise ResearchDbError(
                    f"Sample {item['sample_key']} status 不能从 {old_status} 变为 {item['status']}。"
                )
            if old_status != item["status"]:
                connection.execute(
                    "UPDATE study_samples SET status = ? WHERE id = ?",
                    (item["status"], sample_id),
                )
        sample_ids[item["sample_key"]] = sample_id

    for item in parsed:
        parent_key = item["parent_sample_key"]
        if parent_key is None:
            continue
        if parent_key == item["sample_key"]:
            raise ResearchDbError("Sample 不能把自己设为 parent_sample。")
        parent_id = sample_ids.get(parent_key)
        if parent_id is None:
            parent = connection.execute(
                "SELECT id FROM study_samples WHERE study_id = ? AND sample_key = ?",
                (study_id, parent_key),
            ).fetchone()
            if parent is None:
                raise ResearchDbError(f"parent_sample_key 不存在：{parent_key}")
            parent_id = int(parent["id"])
        sample_id = sample_ids[item["sample_key"]]
        existing_parent = connection.execute(
            "SELECT parent_sample_id FROM study_samples WHERE id = ?", (sample_id,)
        ).fetchone()["parent_sample_id"]
        if existing_parent is not None and int(existing_parent) != parent_id:
            raise ResearchDbError(f"Sample {item['sample_key']} 的 parent_sample 不可静默改写。")
        connection.execute(
            "UPDATE study_samples SET parent_sample_id = COALESCE(parent_sample_id, ?) WHERE id = ?",
            (parent_id, sample_id),
        )
    return sample_ids


def _record_assays(
    connection: Any,
    study_id: int,
    items: object,
    sample_ids: dict[str, int],
    now: str,
) -> None:
    if items is None:
        return
    if not isinstance(items, list):
        raise ResearchDbError("assays 必须是 JSON array。")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"assay {index} 必须是 JSON object。")
        slug = common.slug(item.get("slug"), field="assay slug")
        assay_type = common.text(item.get("assay_type"), required=True, field="assay_type")
        assert assay_type is not None
        status = common.enum_value(
            item.get("status"), ASSAY_STATUSES, default="completed", field="assay status"
        )
        started_at = common.text(item.get("started_at"))
        completed_at = common.text(item.get("completed_at"))
        started_time = (
            common.parse_timestamp(started_at, field="assay started_at")
            if started_at
            else None
        )
        now_time = common.parse_timestamp(now, field="recorded_at")
        if started_time is not None and started_time > now_time:
            raise ResearchDbError(f"Assay {slug} 的 started_at 不能晚于当前记录时间。")
        fields = {
            "assay_type": assay_type,
            "measurement_target": common.text(item.get("measurement_target")),
            "protocol_ref": common.text(item.get("protocol_ref")),
            "batch": common.text(item.get("batch")),
            "run": common.text(item.get("run")),
            "instrument": common.text(item.get("instrument")),
            "operator": common.text(item.get("operator")),
            "started_at": started_at,
            "metadata_json": _metadata_json(item.get("metadata"), field="assay metadata"),
        }
        existing = connection.execute(
            "SELECT * FROM study_assays WHERE study_id = ? AND slug = ?", (study_id, slug)
        ).fetchone()
        if completed_at is None:
            if existing is not None and existing["completed_at"] is not None:
                completed_at = str(existing["completed_at"])
            elif status == "completed":
                completed_at = now
        completed_time = (
            common.parse_timestamp(completed_at, field="assay completed_at")
            if completed_at
            else None
        )
        if completed_time is not None:
            if started_time is not None and completed_time < started_time:
                raise ResearchDbError(f"Assay {slug} 的 completed_at 不能早于 started_at。")
            if completed_time > now_time:
                raise ResearchDbError(f"Assay {slug} 的 completed_at 不能晚于当前记录时间。")

        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO study_assays(
                    study_id, slug, assay_type, measurement_target, protocol_ref,
                    batch, run, instrument, operator, status, started_at,
                    completed_at, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    slug,
                    fields["assay_type"],
                    fields["measurement_target"],
                    fields["protocol_ref"],
                    fields["batch"],
                    fields["run"],
                    fields["instrument"],
                    fields["operator"],
                    status,
                    fields["started_at"],
                    completed_at,
                    fields["metadata_json"],
                    now,
                ),
            )
            assay_id = int(cursor.lastrowid)
        else:
            assay_id = int(existing["id"])
            changed = [
                field
                for field, value in fields.items()
                if (existing[field] if existing[field] is not None else None) != value
            ]
            if changed:
                raise ResearchDbError(
                    f"Assay {slug} 的实际执行身份字段不可静默改写：" + ", ".join(changed)
                )
            old_status = str(existing["status"])
            if status not in _ASSAY_TRANSITIONS[old_status]:
                raise ResearchDbError(f"Assay {slug} status 不能从 {old_status} 变为 {status}。")
            if old_status == "completed" and completed_at and completed_at != existing["completed_at"]:
                raise ResearchDbError(f"completed Assay {slug} 不能修改 completed_at。")
            connection.execute(
                "UPDATE study_assays SET status = ?, completed_at = COALESCE(completed_at, ?) WHERE id = ?",
                (status, completed_at, assay_id),
            )

        sample_keys = item.get("sample_keys", [])
        if not isinstance(sample_keys, list) or not all(isinstance(key, str) for key in sample_keys):
            raise ResearchDbError("assay sample_keys 必须是字符串数组。")
        for sample_key in sample_keys:
            sample_id = sample_ids.get(sample_key)
            if sample_id is None:
                sample = connection.execute(
                    "SELECT id FROM study_samples WHERE study_id = ? AND sample_key = ?",
                    (study_id, sample_key),
                ).fetchone()
                if sample is None:
                    raise ResearchDbError(f"Assay {slug} 引用不存在的 Sample：{sample_key}")
                sample_id = int(sample["id"])
            connection.execute(
                "INSERT OR IGNORE INTO study_assay_samples(assay_id, sample_id) VALUES (?, ?)",
                (assay_id, sample_id),
            )


def _record_deviations(connection: Any, study_id: int, items: object, now: str) -> None:
    if items is None:
        return
    if not isinstance(items, list):
        raise ResearchDbError("deviations 必须是 JSON array。")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"deviation {index} 必须是 JSON object。")
        deviation_key = common.slug(item.get("deviation_key"), field="deviation_key")
        description = common.text(item.get("description"), required=True, field="deviation description")
        scientific_impact = common.text(
            item.get("scientific_impact"), required=True, field="deviation scientific_impact"
        )
        assert description is not None and scientific_impact is not None
        existing = connection.execute(
            "SELECT * FROM study_deviations WHERE study_id = ? AND deviation_key = ?",
            (study_id, deviation_key),
        ).fetchone()
        values = {
            "description": description,
            "reason": common.text(item.get("reason")),
            "affected_units": common.text(item.get("affected_units")),
            "scientific_impact": scientific_impact,
            "occurred_at": common.text(item.get("occurred_at")),
        }
        if values["occurred_at"]:
            common.parse_timestamp(values["occurred_at"], field="deviation occurred_at")
        if existing is None:
            connection.execute(
                """
                INSERT INTO study_deviations(
                    study_id, deviation_key, description, reason, affected_units,
                    scientific_impact, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    deviation_key,
                    values["description"],
                    values["reason"],
                    values["affected_units"],
                    values["scientific_impact"],
                    values["occurred_at"],
                    now,
                ),
            )
        else:
            changed = [
                field
                for field, value in values.items()
                if (existing[field] if existing[field] is not None else None) != value
            ]
            if changed:
                raise ResearchDbError(
                    f"Study deviation {deviation_key} 是追加式事件，不能静默改写："
                    + ", ".join(changed)
                )


def _record_artifacts(project_root: Path, connection: Any, study_id: int, items: object, now: str) -> None:
    if items is None:
        return
    if not isinstance(items, list):
        raise ResearchDbError("study artifacts 必须是 JSON array。")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"study artifact {index} 必须是 JSON object。")
        role = common.enum_value(
            item.get("role"), STUDY_ARTIFACT_ROLES, default="other", field="study artifact role"
        )
        storage_kind = common.enum_value(
            item.get("storage_kind"), STORAGE_KINDS, default="local", field="storage_kind"
        )
        git_tracking = common.tracking(item.get("git_tracking"))
        tracking_reason = common.text(item.get("tracking_reason"))
        if git_tracking == "not_required" and not tracking_reason:
            raise ResearchDbError("study artifact git_tracking=not_required 时必须说明 tracking_reason。")
        if storage_kind == "local":
            location = common.local_path(
                project_root, item.get("location"), field="study artifact location"
            )
        else:
            location = common.text(item.get("location"), required=True, field="study artifact location")
            assert location is not None
            if git_tracking == "required":
                raise ResearchDbError("external study artifact 不能声明 git_tracking=required。")
        existing = connection.execute(
            "SELECT * FROM study_artifacts WHERE study_id = ? AND location = ?",
            (study_id, location),
        ).fetchone()
        values = {
            "role": role,
            "storage_kind": storage_kind,
            "git_tracking": git_tracking,
            "tracking_reason": tracking_reason,
            "version": common.text(item.get("version")),
        }
        if existing is None:
            connection.execute(
                """
                INSERT INTO study_artifacts(
                    study_id, role, location, storage_kind, git_tracking,
                    tracking_reason, version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    role,
                    location,
                    storage_kind,
                    git_tracking,
                    tracking_reason,
                    values["version"],
                    now,
                ),
            )
        else:
            changed = [
                field
                for field, value in values.items()
                if (existing[field] if existing[field] is not None else None) != value
            ]
            if changed:
                raise ResearchDbError(
                    "已登记 Study artifact 的 provenance 不可静默改写：" + ", ".join(changed)
                )


def record_study(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    title = common.text(bundle.get("title"), required=True, field="title")
    design_slug = common.slug(bundle.get("design_slug"), field="design_slug")
    study_type = common.text(bundle.get("study_type"))
    status = common.enum_value(bundle.get("status"), STUDY_STATUSES, default="in_progress", field="study status")
    provenance_path = common.local_path(
        project_root, bundle.get("provenance_path"), field="study provenance_path", require_file=True
    )
    started_at = common.text(bundle.get("started_at"), required=True, field="started_at")
    assert title is not None and started_at is not None
    started_time = common.parse_timestamp(started_at, field="started_at")
    completed_at = common.text(bundle.get("completed_at"))
    now = common.now()
    now_time = common.parse_timestamp(now, field="recorded_at")
    if started_time > now_time:
        raise ResearchDbError("started_at 不能晚于当前记录时间。")
    if completed_at:
        completed_time = common.parse_timestamp(completed_at, field="completed_at")
        if completed_time < started_time:
            raise ResearchDbError("completed_at 不能早于 started_at。")
        if completed_time > now_time:
            raise ResearchDbError("completed_at 不能晚于当前记录时间。")

    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            design = connection.execute(
                "SELECT id, status FROM research_designs WHERE slug = ?", (design_slug,)
            ).fetchone()
            if design is None:
                raise ResearchDbError(f"Study 引用不存在的 Research Design：{design_slug}")
            if design["status"] not in {"frozen", "execution_ready"}:
                raise ResearchDbError("Study 开始前，关联 Research Design 必须已经 frozen 或 execution_ready。")
            design_id = int(design["id"])
            existing = connection.execute("SELECT * FROM studies WHERE slug = ?", (slug,)).fetchone()
            if completed_at is None:
                if existing is not None and existing["completed_at"] is not None:
                    completed_at = str(existing["completed_at"])
                elif status == "completed":
                    completed_at = now
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO studies(
                        slug, title, design_id, study_type, status, provenance_path,
                        started_at, completed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        title,
                        design_id,
                        study_type,
                        status,
                        provenance_path,
                        started_at,
                        completed_at,
                        now,
                        now,
                    ),
                )
                study_id = int(cursor.lastrowid)
            else:
                study_id = int(existing["id"])
                immutable = {
                    "title": title,
                    "design_id": design_id,
                    "study_type": study_type,
                    "provenance_path": provenance_path,
                    "started_at": started_at,
                }
                changed = [
                    field
                    for field, value in immutable.items()
                    if (existing[field] if existing[field] is not None else None) != value
                ]
                if changed:
                    raise ResearchDbError(
                        "Study 实际执行身份字段不可静默改写：" + ", ".join(changed)
                    )
                old_status = str(existing["status"])
                if status not in _STUDY_TRANSITIONS[old_status]:
                    raise ResearchDbError(f"Study status 不能从 {old_status} 变为 {status}。")
                if old_status == "completed" and completed_at and completed_at != existing["completed_at"]:
                    raise ResearchDbError("completed Study 不能修改 completed_at。")
                connection.execute(
                    """
                    UPDATE studies
                    SET status = ?, completed_at = COALESCE(completed_at, ?), updated_at = ?
                    WHERE id = ?
                    """,
                    (status, completed_at, now, study_id),
                )

            sample_ids = _record_samples(connection, study_id, bundle.get("samples"), now)
            _record_assays(connection, study_id, bundle.get("assays"), sample_ids, now)
            _record_deviations(connection, study_id, bundle.get("deviations"), now)
            _record_artifacts(project_root, connection, study_id, bundle.get("artifacts"), now)

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'study_recorded', 'study', ?, ?, ?)
                """,
                (
                    now,
                    str(study_id),
                    "Actual Study execution entered canonical provenance.",
                    f"study={slug}; design={design_slug}; status={status}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {"ok": True, "study_id": study_id, "slug": slug, "status": status}


def list_studies(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        studies: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT s.*, d.slug AS design_slug
            FROM studies s
            JOIN research_designs d ON d.id = s.design_id
            ORDER BY s.id LIMIT ?
            """,
            (limit,),
        ):
            item = dict(row)
            study_id = int(row["id"])
            item["samples"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM study_samples WHERE study_id = ? ORDER BY id", (study_id,)
                )
            ]
            item["assays"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM study_assays WHERE study_id = ? ORDER BY id", (study_id,)
                )
            ]
            item["deviations"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM study_deviations WHERE study_id = ? ORDER BY id", (study_id,)
                )
            ]
            item["artifacts"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM study_artifacts WHERE study_id = ? ORDER BY id", (study_id,)
                )
            ]
            studies.append(item)
    return {"ok": True, "studies": studies}
