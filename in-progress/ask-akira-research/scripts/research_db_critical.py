from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_db_bundle import (
    _array,
    _checked_artifacts,
    _depth,
    _insert_relations,
    _json_text,
    _now,
    _paper,
    _register_ref,
    _resolve_entity,
    _source_fields,
    _string_list,
    _text,
    _write_change,
)
from research_db_core import ResearchDbError, connect, database_path


def _sidecar_path(project_root: Path, value: object) -> str | None:
    raw = _text(value)
    if raw is None:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_root / path
    path = path.resolve()
    if not path.is_file():
        raise ResearchDbError(f"sidecar 文件不存在：{path}")
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def ingest_critical(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")
    paper_id = _text(bundle.get("paper_id"), required=True, field="paper_id")
    requested_depth = _text(bundle.get("depth")) or "full_scan"
    if requested_depth not in {"full_scan", "deep_extraction"}:
        raise ResearchDbError("depth 必须是 full_scan 或 deep_extraction。")
    sections = _string_list(bundle.get("sections_checked"), "sections_checked", required=True)
    timestamp = _now()
    started_at = _text(bundle.get("started_at")) or timestamp
    completed_at = _text(bundle.get("completed_at")) or timestamp
    reason = _text(bundle.get("reason")) or "Pass 2 Critical Audit"
    issues = _array(bundle, "issues")
    relations = _array(bundle, "relations")
    sidecar = _sidecar_path(project_root, bundle.get("sidecar_path"))

    refs: dict[tuple[str, str], str] = {}
    counts = {"issues": 0, "relations": 0}
    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            paper = _paper(connection, paper_id)
            reconstructed = connection.execute(
                """
                SELECT 1 FROM reading_runs
                WHERE paper_id = ? AND pass = 'reconstruction' AND completed_at IS NOT NULL
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
            if reconstructed is None:
                raise ResearchDbError(f"{paper_id} 尚未完成 Reconstruction。")
            existing = connection.execute(
                """
                SELECT 1 FROM reading_runs
                WHERE paper_id = ? AND pass = 'critical_audit' AND completed_at IS NOT NULL
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
            if existing:
                raise ResearchDbError(f"{paper_id} 已有完成的 critical audit run。")
            checked = _checked_artifacts(connection, paper_id, bundle.get("artifacts_checked"))
            run_cursor = connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked, notes
                ) VALUES (?, 'critical_audit', ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    requested_depth,
                    started_at,
                    completed_at,
                    json.dumps(checked, ensure_ascii=False),
                    json.dumps(sections, ensure_ascii=False),
                    _text(bundle.get("notes")),
                ),
            )
            run_id = int(run_cursor.lastrowid)

            for spec in issues:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Issue"
                )
                target_type = _text(spec.get("target_type"))
                target_ref = _text(spec.get("target_ref"))
                target_id = _text(spec.get("target_id"))
                resolved_target_id = None
                if target_type or target_ref or target_id:
                    target_spec = {
                        "target_type": target_type,
                        "target_ref": target_ref,
                        "target_id": target_id,
                    }
                    target_type, resolved_target_id = _resolve_entity(
                        connection, paper_id, refs, target_spec, "target"
                    )
                cursor = connection.execute(
                    """
                    INSERT INTO issues(
                        paper_id, category, nature, target_type, target_id, assessment,
                        basis, severity, confidence, why_it_matters,
                        alternative_explanations, possible_resolution,
                        artifact_id, source_locator, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        _text(spec.get("category"), required=True, field="issue.category"),
                        _text(spec.get("nature"), required=True, field="issue.nature"),
                        target_type,
                        resolved_target_id,
                        _text(spec.get("assessment"), required=True, field="issue.assessment"),
                        _text(spec.get("basis"), required=True, field="issue.basis"),
                        _text(spec.get("severity"), required=True, field="issue.severity"),
                        _text(spec.get("confidence"), required=True, field="issue.confidence"),
                        _text(spec.get("why_it_matters")),
                        _json_text(spec.get("alternative_explanations")),
                        _text(spec.get("possible_resolution")),
                        artifact_id,
                        locator,
                        timestamp,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "issue", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="issue", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Issue: {spec.get('assessment')}")
                counts["issues"] += 1

            counts["relations"] = _insert_relations(
                connection, paper_id, refs, relations, timestamp, reason, run_id
            )
            new_depth = _depth(str(paper["read_depth"]), requested_depth)
            connection.execute(
                """
                UPDATE papers
                SET status = 'active', read_depth = ?, reading_status = 'extracted',
                    critical_status = 'critically_reviewed',
                    sidecar_path = COALESCE(?, sidecar_path), updated_at = ?
                WHERE id = ?
                """,
                (new_depth, sidecar, timestamp, paper_id),
            )
            _write_change(connection, timestamp=timestamp, entity_type="reading_run", entity_id=str(run_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Completed critical audit ({requested_depth})")
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

    return {
        "ok": True,
        "paper_id": paper_id,
        "reading_run_id": run_id,
        "pass": "critical_audit",
        "depth": requested_depth,
        "reading_status": "extracted",
        "critical_status": "critically_reviewed",
        "sidecar_path": sidecar,
        "counts": counts,
        "refs": {f"{kind}:{ref}": entity_id for (kind, ref), entity_id in refs.items()},
    }
