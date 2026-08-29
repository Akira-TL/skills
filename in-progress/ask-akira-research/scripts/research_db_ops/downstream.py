from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_db_core import ResearchDbError, connect
from research_db_ops.discovery import _db_path, _enum, _now, _text


DATASET_ROLES = {"raw", "curated", "metadata", "manifest", "other"}
STORAGE_KINDS = {"local", "external"}
GIT_TRACKING = {"required", "not_required"}
ANALYSIS_MODES = {"confirmatory", "exploratory"}
ANALYSIS_STATUSES = {"planned", "frozen", "completed", "abandoned"}
ANALYSIS_ARTIFACT_ROLES = {"estimate", "diagnostic", "figure", "table", "log", "other"}
ANALYSIS_ARTIFACT_TIMING_ROLES = {"pre_result_support", "result"}
DATASET_ARTIFACT_TIMING_ROLES = {"pre_result_input", "post_result_context"}
AMENDMENT_TIMINGS = {"pre_result", "post_result"}
_STATUS_ORDER = {"planned": 0, "frozen": 1, "completed": 2, "abandoned": 2}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _slug(value: object, *, field: str = "slug") -> str:
    text = _text(value, required=True, field=field)
    assert text is not None
    if not _SLUG_RE.fullmatch(text):
        raise ResearchDbError(f"{field} 必须使用 lowercase kebab-case。")
    return text


def _local_path(project_root: Path, value: object, *, field: str) -> str:
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
    if not resolved.exists():
        raise ResearchDbError(f"{field} 指向的文件不存在：{relative.as_posix()}")
    return relative.as_posix()


def _tracking(value: object, *, default: str = "required") -> str:
    return _enum(value, GIT_TRACKING, default=default, field="git_tracking")


def record_dataset(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(bundle.get("slug"))
    title = _text(bundle.get("title"), required=True, field="title")
    source = _text(bundle.get("source"), required=True, field="source")
    received_at = _text(bundle.get("received_at"), required=True, field="received_at")
    unit = _text(bundle.get("unit_of_inference"), required=True, field="unit_of_inference")
    provenance_path = _local_path(project_root, bundle.get("provenance_path"), field="provenance_path")
    identity = _text(bundle.get("identity"))
    source_url = _text(bundle.get("source_url"))
    version = _text(bundle.get("version"))
    status = _enum(bundle.get("status"), {"active", "archived"}, default="active", field="status")
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ResearchDbError("dataset artifacts 必须是非空数组。")

    parsed_artifacts: list[dict[str, Any]] = []
    for index, item in enumerate(artifacts, start=1):
        if not isinstance(item, dict):
            raise ResearchDbError(f"dataset artifact {index} 必须是 JSON object。")
        role = _enum(item.get("role"), DATASET_ROLES, default="other", field="dataset artifact role")
        storage_kind = _enum(
            item.get("storage_kind"), STORAGE_KINDS, default="local", field="storage_kind"
        )
        git_tracking = _tracking(item.get("git_tracking"))
        tracking_reason = _text(item.get("tracking_reason"))
        if git_tracking == "not_required" and not tracking_reason:
            raise ResearchDbError("git_tracking=not_required 时必须说明 tracking_reason。")
        if storage_kind == "local":
            location = _local_path(project_root, item.get("location"), field="dataset artifact location")
        else:
            location = _text(item.get("location"), required=True, field="dataset artifact location")
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
                "source_url": _text(item.get("source_url")),
                "version": _text(item.get("version")),
            }
        )

    now = _now()
    with connect(_db_path(project_root)) as connection:
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


def _dataset_ids(connection, slugs: object) -> list[int]:
    if not isinstance(slugs, list) or not slugs or not all(isinstance(v, str) for v in slugs):
        raise ResearchDbError("dataset_slugs 必须是非空字符串数组。")
    ids: list[int] = []
    for slug in slugs:
        row = connection.execute("SELECT id FROM datasets WHERE slug = ?", (slug.strip(),)).fetchone()
        if row is None:
            raise ResearchDbError(f"Analysis 引用不存在的 Dataset：{slug}")
        dataset_id = int(row["id"])
        if dataset_id not in ids:
            ids.append(dataset_id)
    return ids


def record_analysis(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(bundle.get("slug"))
    title = _text(bundle.get("title"), required=True, field="title")
    analysis_mode = _enum(
        bundle.get("analysis_mode"), ANALYSIS_MODES, default="confirmatory", field="analysis_mode"
    )
    status = _enum(bundle.get("status"), ANALYSIS_STATUSES, default="planned", field="status")
    target_uncertainty = _text(
        bundle.get("target_uncertainty"), required=True, field="target_uncertainty"
    )
    estimand = _text(bundle.get("estimand"), required=True, field="estimand")
    unit = _text(bundle.get("unit_of_inference"), required=True, field="unit_of_inference")
    primary_analysis = _text(bundle.get("primary_analysis"), required=True, field="primary_analysis")
    analysis_path = _local_path(project_root, bundle.get("analysis_path"), field="analysis_path")
    code_path = _local_path(project_root, bundle.get("code_path"), field="code_path")
    freeze_commit = _text(bundle.get("freeze_commit"))
    started_at = _text(bundle.get("started_at")) or _now()
    completed_at = _text(bundle.get("completed_at"))
    if status == "completed" and not completed_at:
        completed_at = _now()
    if analysis_mode == "confirmatory" and status in {"frozen", "completed"} and not freeze_commit:
        raise ResearchDbError("confirmatory analysis 进入 frozen/completed 时必须记录结果可见前的 freeze_commit。")

    artifacts = bundle.get("artifacts", [])
    dataset_artifact_timing = bundle.get("dataset_artifact_timing", [])
    amendments = bundle.get("amendments", [])
    observations = bundle.get("observations", [])
    if not all(
        isinstance(value, list)
        for value in (artifacts, dataset_artifact_timing, amendments, observations)
    ):
        raise ResearchDbError(
            "artifacts/dataset_artifact_timing/amendments/observations 必须是数组。"
        )

    now = _now()
    with connect(_db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            dataset_ids = _dataset_ids(connection, bundle.get("dataset_slugs"))
            existing = connection.execute("SELECT * FROM analysis_runs WHERE slug = ?", (slug,)).fetchone()
            design_slug = _text(bundle.get("design_slug"))
            design_id: int | None = None
            if design_slug is not None:
                design = connection.execute(
                    "SELECT id, target_estimand, status FROM research_designs WHERE slug = ?",
                    (design_slug,),
                ).fetchone()
                if design is None:
                    raise ResearchDbError(f"Analysis 引用不存在的 Research Design：{design_slug}")
                if analysis_mode == "confirmatory" and design["status"] not in {"frozen", "execution_ready"}:
                    raise ResearchDbError("confirmatory Analysis 引用的 Research Design 必须先冻结。")
                if str(design["target_estimand"]).strip() != str(estimand).strip():
                    raise ResearchDbError("Analysis estimand 与关联 Research Design 的 target_estimand 不一致。")
                design_id = int(design["id"])
            elif existing is not None and existing["design_id"] is not None:
                design_id = int(existing["design_id"])
            elif analysis_mode == "confirmatory":
                matching_designs = connection.execute(
                    """
                    SELECT d.id
                    FROM research_designs d
                    JOIN hypothesis_sets h ON h.id = d.hypothesis_set_id
                    WHERE d.status <> 'superseded'
                      AND (
                        trim(d.target_estimand) = trim(?)
                        OR trim(h.target_uncertainty) = trim(?)
                      )
                    ORDER BY d.id
                    """,
                    (estimand, target_uncertainty),
                ).fetchall()
                if matching_designs:
                    raise ResearchDbError(
                        "confirmatory Analysis 与已登记 Research Design 匹配时必须显式提供 design_slug，"
                        "不能只靠重复文本形成隐式关联。"
                    )

            immutable = {
                "title": title,
                "analysis_mode": analysis_mode,
                "target_uncertainty": target_uncertainty,
                "estimand": estimand,
                "unit_of_inference": unit,
                "primary_analysis": primary_analysis,
                "analysis_path": analysis_path,
                "code_path": code_path,
                "design_id": design_id,
            }
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO analysis_runs(
                        slug, title, analysis_mode, status, target_uncertainty, estimand,
                        unit_of_inference, primary_analysis, analysis_path, code_path,
                        freeze_commit, started_at, completed_at, created_at, updated_at,
                        design_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        title,
                        analysis_mode,
                        status,
                        target_uncertainty,
                        estimand,
                        unit,
                        primary_analysis,
                        analysis_path,
                        code_path,
                        freeze_commit,
                        started_at,
                        completed_at,
                        now,
                        now,
                        design_id,
                    ),
                )
                analysis_id = int(cursor.lastrowid)
            else:
                analysis_id = int(existing["id"])
                if existing["status"] in {"frozen", "completed"}:
                    changed = [
                        key
                        for key, value in immutable.items()
                        if str(existing[key]) != str(value)
                        and not (
                            key == "design_id"
                            and existing["design_id"] is None
                            and value is not None
                        )
                    ]
                    if changed:
                        raise ResearchDbError(
                            "Analysis 在 frozen/completed 后不能静默修改预先定义字段："
                            + ", ".join(changed)
                            + "。需要新 Analysis 或明确的上游设计修订。"
                        )
                if existing["status"] == "completed" and status != "completed":
                    raise ResearchDbError("completed Analysis 不能回退状态。")
                if existing["status"] == "abandoned":
                    raise ResearchDbError("abandoned Analysis 不能重新激活；请建立新的 Analysis。")
                if _STATUS_ORDER[status] < _STATUS_ORDER[str(existing["status"])]:
                    raise ResearchDbError("Analysis status 不能回退。")
                if existing["status"] == "planned":
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET title = ?, analysis_mode = ?, status = ?, target_uncertainty = ?,
                            estimand = ?, unit_of_inference = ?, primary_analysis = ?,
                            analysis_path = ?, code_path = ?, freeze_commit = COALESCE(?, freeze_commit),
                            completed_at = COALESCE(?, completed_at), updated_at = ?, design_id = ?
                        WHERE id = ?
                        """,
                        (
                            title,
                            analysis_mode,
                            status,
                            target_uncertainty,
                            estimand,
                            unit,
                            primary_analysis,
                            analysis_path,
                            code_path,
                            freeze_commit,
                            completed_at,
                            now,
                            design_id,
                            analysis_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = ?, freeze_commit = COALESCE(?, freeze_commit),
                            completed_at = COALESCE(?, completed_at), updated_at = ?,
                            design_id = COALESCE(design_id, ?)
                        WHERE id = ?
                        """,
                        (status, freeze_commit, completed_at, now, design_id, analysis_id),
                    )

            for dataset_id in dataset_ids:
                connection.execute(
                    "INSERT OR IGNORE INTO analysis_inputs(analysis_id, dataset_id, role) VALUES (?, ?, 'primary')",
                    (analysis_id, dataset_id),
                )

            for index, item in enumerate(dataset_artifact_timing, start=1):
                if not isinstance(item, dict):
                    raise ResearchDbError(
                        f"dataset artifact timing {index} 必须是 JSON object。"
                    )
                dataset_slug = _slug(
                    item.get("dataset_slug"), field="dataset artifact timing dataset_slug"
                )
                dataset_row = connection.execute(
                    "SELECT id FROM datasets WHERE slug = ?", (dataset_slug,)
                ).fetchone()
                if dataset_row is None or int(dataset_row["id"]) not in dataset_ids:
                    raise ResearchDbError(
                        f"dataset artifact timing 必须引用当前 Analysis 的 Dataset：{dataset_slug}"
                    )
                location = _local_path(
                    project_root,
                    item.get("location"),
                    field="dataset artifact timing location",
                )
                artifact_row = connection.execute(
                    """
                    SELECT id, storage_kind, git_tracking
                    FROM dataset_artifacts
                    WHERE dataset_id = ? AND location = ?
                    """,
                    (int(dataset_row["id"]), location),
                ).fetchone()
                if artifact_row is None:
                    raise ResearchDbError(
                        "dataset artifact timing 引用的 artifact 未登记在对应 Dataset："
                        + location
                    )
                if artifact_row["storage_kind"] != "local" or artifact_row["git_tracking"] != "required":
                    raise ResearchDbError(
                        "dataset artifact timing 只用于 local + git_tracking=required 的 canonical artifact。"
                    )
                timing_role = _enum(
                    item.get("timing_role"),
                    DATASET_ARTIFACT_TIMING_ROLES,
                    default="pre_result_input",
                    field="dataset artifact timing_role",
                )
                reason = _text(item.get("reason"))
                if timing_role == "post_result_context" and not reason:
                    raise ResearchDbError(
                        "dataset artifact timing_role=post_result_context 时必须说明 reason。"
                    )
                existing_timing = connection.execute(
                    """
                    SELECT timing_role, reason
                    FROM analysis_dataset_artifact_timing
                    WHERE analysis_id = ? AND dataset_artifact_id = ?
                    """,
                    (analysis_id, int(artifact_row["id"])),
                ).fetchone()
                if existing_timing is not None:
                    if (
                        str(existing_timing["timing_role"]) != timing_role
                        or (existing_timing["reason"] or None) != reason
                    ):
                        raise ResearchDbError(
                            "已登记的 Dataset artifact timing 不可静默改写；"
                            "需要建立新的 Analysis 或保留原时序关系。"
                        )
                    continue
                connection.execute(
                    """
                    INSERT INTO analysis_dataset_artifact_timing(
                        analysis_id, dataset_artifact_id, timing_role, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (analysis_id, int(artifact_row["id"]), timing_role, reason, now),
                )

            artifact_ids_by_path: dict[str, int] = {}
            for index, item in enumerate(artifacts, start=1):
                if not isinstance(item, dict):
                    raise ResearchDbError(f"analysis artifact {index} 必须是 JSON object。")
                role = _enum(
                    item.get("role"), ANALYSIS_ARTIFACT_ROLES, default="other", field="analysis artifact role"
                )
                path = _local_path(project_root, item.get("path"), field="analysis artifact path")
                git_tracking = _tracking(item.get("git_tracking"))
                timing_role = _enum(
                    item.get("timing_role"),
                    ANALYSIS_ARTIFACT_TIMING_ROLES,
                    default="result",
                    field="analysis artifact timing_role",
                )
                tracking_reason = _text(item.get("tracking_reason"))
                if git_tracking == "not_required" and not tracking_reason:
                    raise ResearchDbError("analysis artifact git_tracking=not_required 时必须说明 tracking_reason。")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO analysis_artifacts(
                        analysis_id, role, path, git_tracking, tracking_reason, created_at,
                        timing_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (analysis_id, role, path, git_tracking, tracking_reason, now, timing_role),
                )
                row = connection.execute(
                    "SELECT id FROM analysis_artifacts WHERE analysis_id = ? AND path = ?",
                    (analysis_id, path),
                ).fetchone()
                assert row is not None
                artifact_ids_by_path[path] = int(row["id"])

            for index, item in enumerate(amendments, start=1):
                if not isinstance(item, dict):
                    raise ResearchDbError(f"analysis amendment {index} 必须是 JSON object。")
                timing = _enum(
                    item.get("timing"), AMENDMENT_TIMINGS, default="post_result", field="amendment timing"
                )
                description = _text(item.get("description"), required=True, field="amendment description")
                reason = _text(item.get("reason"), required=True, field="amendment reason")
                connection.execute(
                    """
                    INSERT INTO analysis_amendments(
                        analysis_id, timing, description, reason, commit_ref, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (analysis_id, timing, description, reason, _text(item.get("commit_ref")), now),
                )

            for index, item in enumerate(observations, start=1):
                if not isinstance(item, dict):
                    raise ResearchDbError(f"project observation {index} 必须是 JSON object。")
                statement = _text(item.get("statement"), required=True, field="observation statement")
                source_path = _local_path(project_root, item.get("source_path"), field="observation source_path")
                artifact_id = artifact_ids_by_path.get(source_path)
                if artifact_id is None:
                    row = connection.execute(
                        "SELECT id FROM analysis_artifacts WHERE analysis_id = ? AND path = ?",
                        (analysis_id, source_path),
                    ).fetchone()
                    if row is None:
                        raise ResearchDbError(
                            f"Project Observation 的 source_path 未登记为当前 Analysis artifact：{source_path}"
                        )
                    artifact_id = int(row["id"])
                statistics = item.get("statistics")
                statistics_json = None if statistics is None else json.dumps(statistics, ensure_ascii=False, sort_keys=True)
                connection.execute(
                    """
                    INSERT INTO project_observations(
                        analysis_id, statement, effect, statistics_json, scope,
                        source_artifact_id, source_locator, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis_id,
                        statement,
                        _text(item.get("effect")),
                        statistics_json,
                        _text(item.get("scope")),
                        artifact_id,
                        _text(item.get("source_locator")),
                        now,
                    ),
                )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'analysis_recorded', 'analysis_run', ?, ?, ?)
                """,
                (
                    now,
                    str(analysis_id),
                    f"Analysis state recorded as {status}.",
                    f"analysis={slug}; mode={analysis_mode}; status={status}; datasets={len(dataset_ids)}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"ok": True, "analysis_id": analysis_id, "slug": slug, "status": status}


def list_datasets(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(_db_path(project_root)) as connection:
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


def list_analyses(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(_db_path(project_root)) as connection:
        rows = []
        for row in connection.execute("SELECT * FROM analysis_runs ORDER BY id LIMIT ?", (limit,)):
            item = dict(row)
            if row["design_id"] is not None:
                design = connection.execute(
                    "SELECT slug FROM research_designs WHERE id = ?", (int(row["design_id"]),)
                ).fetchone()
                item["design_slug"] = str(design["slug"]) if design else None
            else:
                item["design_slug"] = None
            item["dataset_slugs"] = [
                x["slug"]
                for x in connection.execute(
                    """
                    SELECT d.slug FROM analysis_inputs ai
                    JOIN datasets d ON d.id = ai.dataset_id
                    WHERE ai.analysis_id = ? ORDER BY d.id
                    """,
                    (row["id"],),
                )
            ]
            item["dataset_artifact_timing"] = [
                dict(x)
                for x in connection.execute(
                    """
                    SELECT d.slug AS dataset_slug, da.location, t.timing_role, t.reason,
                           t.created_at
                    FROM analysis_dataset_artifact_timing t
                    JOIN dataset_artifacts da ON da.id = t.dataset_artifact_id
                    JOIN datasets d ON d.id = da.dataset_id
                    WHERE t.analysis_id = ?
                    ORDER BY da.id
                    """,
                    (row["id"],),
                )
            ]
            item["artifacts"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM analysis_artifacts WHERE analysis_id = ? ORDER BY id", (row["id"],)
                )
            ]
            item["amendments"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM analysis_amendments WHERE analysis_id = ? ORDER BY id", (row["id"],)
                )
            ]
            item["observations"] = [
                dict(x)
                for x in connection.execute(
                    "SELECT * FROM project_observations WHERE analysis_id = ? ORDER BY id", (row["id"],)
                )
            ]
            rows.append(item)
    return {"ok": True, "analyses": rows}
