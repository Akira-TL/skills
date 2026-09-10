from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import research_db_support.knowledge as knowledge
from research_db_support.storage import ResearchDbError, connect, database_path


def _sidecar_path(project_root: Path, value: object) -> str | None:
    raw = knowledge.text(value)
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
    paper_id = knowledge.text(bundle.get("paper_id"), required=True, field="paper_id")
    requested_depth = knowledge.text(bundle.get("depth")) or "full_scan"
    if requested_depth not in {"full_scan", "deep_extraction"}:
        raise ResearchDbError("depth 必须是 full_scan 或 deep_extraction。")
    sections = knowledge.string_list(bundle.get("sections_checked"), "sections_checked", required=True)
    timestamp = knowledge.now()
    started_at = knowledge.text(bundle.get("started_at")) or timestamp
    completed_at = knowledge.text(bundle.get("completed_at")) or timestamp
    reason = knowledge.text(bundle.get("reason")) or "Pass 2 Critical Audit"
    issues = knowledge.array(bundle, "issues")
    relations = knowledge.array(bundle, "relations")
    sidecar = _sidecar_path(project_root, bundle.get("sidecar_path"))

    refs: dict[tuple[str, str], str] = {}
    counts = {"issues": 0, "relations": 0}
    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            paper = knowledge.paper(connection, paper_id)
            reconstructed = connection.execute(
                """
                SELECT id, depth, completed_at FROM reading_runs
                WHERE paper_id = ? AND pass = 'reconstruction' AND completed_at IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
            if reconstructed is None:
                raise ResearchDbError(f"{paper_id} 尚未完成 Reconstruction。")
            if requested_depth == "deep_extraction" and reconstructed["depth"] != "deep_extraction":
                raise ResearchDbError(
                    f"{paper_id} 的 Critical Audit 不能把 full_scan Reconstruction 升级为 deep_extraction；"
                    "先以 deep_extraction 完成 Reconstruction contract。"
                )
            existing = connection.execute(
                """
                SELECT id, completed_at FROM reading_runs
                WHERE paper_id = ? AND pass = 'critical_audit' AND completed_at IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
            checked = knowledge.checked_artifacts(connection, paper_id, bundle.get("artifacts_checked"))
            if existing:
                if int(reconstructed["id"]) <= int(existing["id"]):
                    raise ResearchDbError(
                        f"{paper_id} 已有完成的 critical audit run，且之后没有新的 Reconstruction。"
                    )
                new_artifact_ids = {
                    int(row["id"])
                    for row in connection.execute(
                        """
                        SELECT id FROM artifacts
                        WHERE paper_id = ? AND created_at > ?
                        ORDER BY id
                        """,
                        (paper_id, existing["completed_at"]),
                    )
                }
                checked_ids = {int(item["id"]) for item in checked}
                missing_new = sorted(new_artifact_ids - checked_ids)
                if missing_new:
                    raise ResearchDbError(
                        "增量 Critical Audit 必须检查上次审计后登记的全部新 artifact："
                        + ", ".join(str(value) for value in missing_new)
                    )
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
                    knowledge.text(bundle.get("notes")),
                ),
            )
            run_id = int(run_cursor.lastrowid)

            for spec in issues:
                artifact_id, locator = knowledge.source_fields(
                    connection, paper_id, spec, required=True, field="Issue"
                )
                basis = knowledge.text(spec.get("basis"), required=True, field="issue.basis")
                basis_rationale = knowledge.text(
                    spec.get("basis_rationale"),
                    required=True,
                    field="issue.basis_rationale",
                )
                target_type = knowledge.text(spec.get("target_type"))
                target_ref = knowledge.text(spec.get("target_ref"))
                target_id = knowledge.text(spec.get("target_id"))
                resolved_target_id = None
                if target_type or target_ref or target_id:
                    target_spec = {
                        "target_type": target_type,
                        "target_ref": target_ref,
                        "target_id": target_id,
                    }
                    target_type, resolved_target_id = knowledge.resolve_entity(
                        connection, paper_id, refs, target_spec, "target"
                    )
                cursor = connection.execute(
                    """
                    INSERT INTO issues(
                        paper_id, category, nature, target_type, target_id, assessment,
                        basis, basis_rationale, severity, confidence, why_it_matters,
                        alternative_explanations, possible_resolution,
                        artifact_id, source_locator, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        knowledge.text(spec.get("category"), required=True, field="issue.category"),
                        knowledge.text(spec.get("nature"), required=True, field="issue.nature"),
                        target_type,
                        resolved_target_id,
                        knowledge.text(spec.get("assessment"), required=True, field="issue.assessment"),
                        basis,
                        basis_rationale,
                        knowledge.text(spec.get("severity"), required=True, field="issue.severity"),
                        knowledge.text(spec.get("confidence"), required=True, field="issue.confidence"),
                        knowledge.text(spec.get("why_it_matters")),
                        knowledge.json_text(spec.get("alternative_explanations")),
                        knowledge.text(spec.get("possible_resolution")),
                        artifact_id,
                        locator,
                        timestamp,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "issue", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="issue", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Issue: {spec.get('assessment')}")
                counts["issues"] += 1

            counts["relations"] = knowledge.insert_relations(
                connection, paper_id, refs, relations, timestamp, reason, run_id
            )
            new_depth = knowledge.depth(str(paper["read_depth"]), requested_depth)
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
            knowledge.write_change(connection, timestamp=timestamp, entity_type="reading_run", entity_id=str(run_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Completed critical audit ({requested_depth})")
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
