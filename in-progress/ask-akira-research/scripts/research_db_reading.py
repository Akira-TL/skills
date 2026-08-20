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
    _source_fields,
    _string_list,
    _text,
    _write_change,
)
from research_db_core import ResearchDbError, connect, database_path


def ingest_reading(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
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
    reason = _text(bundle.get("reason")) or "Pass 1 Reconstruction"

    methods = _array(bundle, "methods")
    experiments = _array(bundle, "experiments")
    observations = _array(bundle, "observations")
    claims = _array(bundle, "claims")
    leads = _array(bundle, "leads")
    relations = _array(bundle, "relations")
    if not any((methods, experiments, observations, claims, leads)):
        raise ResearchDbError("Reconstruction bundle 至少需要一个知识单元。")

    refs: dict[tuple[str, str], str] = {}
    counts = {name: 0 for name in ("methods", "experiments", "observations", "claims", "leads", "relations")}
    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            paper = _paper(connection, paper_id)
            existing = connection.execute(
                """
                SELECT 1 FROM reading_runs
                WHERE paper_id = ? AND pass = 'reconstruction' AND completed_at IS NOT NULL
                LIMIT 1
                """,
                (paper_id,),
            ).fetchone()
            if existing:
                raise ResearchDbError(f"{paper_id} 已有完成的 reconstruction run。")
            checked = _checked_artifacts(connection, paper_id, bundle.get("artifacts_checked"))
            run_cursor = connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked, notes
                ) VALUES (?, 'reconstruction', ?, ?, ?, ?, ?, ?)
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

            for spec in methods:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Method"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO methods(
                        paper_id, name, purpose, description, parameters, materials,
                        software, reusable_notes, artifact_id, source_locator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        _text(spec.get("name"), required=True, field="method.name"),
                        _text(spec.get("purpose")),
                        _text(spec.get("description")),
                        _json_text(spec.get("parameters")),
                        _json_text(spec.get("materials")),
                        _json_text(spec.get("software")),
                        _text(spec.get("reusable_notes")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "method", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="method", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Method: {spec.get('name')}")
                counts["methods"] += 1

            for spec in experiments:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Experiment"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO experiments(
                        paper_id, question, design, samples, groups_json, controls,
                        variables_json, analysis, result_summary, artifact_id, source_locator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        _text(spec.get("question")),
                        _text(spec.get("design")),
                        _text(spec.get("samples")),
                        _json_text(spec.get("groups")),
                        _text(spec.get("controls")),
                        _json_text(spec.get("variables")),
                        _text(spec.get("analysis")),
                        _text(spec.get("result_summary")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "experiment", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="experiment", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Experiment: {spec.get('question') or spec.get('design')}")
                counts["experiments"] += 1

            for spec in observations:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Observation"
                )
                experiment_id = None
                if spec.get("experiment_ref") is not None:
                    key = ("experiment", _text(spec.get("experiment_ref"), required=True, field="observation.experiment_ref"))
                    if key not in refs:
                        raise ResearchDbError(f"未知 bundle ref：experiment:{key[1]}")
                    experiment_id = int(refs[key])
                cursor = connection.execute(
                    """
                    INSERT INTO observations(
                        paper_id, experiment_id, statement, effect, statistics_json,
                        scope, certainty, artifact_id, source_locator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        experiment_id,
                        _text(spec.get("statement"), required=True, field="observation.statement"),
                        _text(spec.get("effect")),
                        _json_text(spec.get("statistics")),
                        _text(spec.get("scope")),
                        _text(spec.get("certainty")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "observation", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="observation", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Observation: {spec.get('statement')}")
                counts["observations"] += 1

            for spec in claims:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Claim"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO claims(
                        paper_id, statement, claim_type, author_strength, scope,
                        artifact_id, source_locator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        _text(spec.get("statement"), required=True, field="claim.statement"),
                        _text(spec.get("claim_type"), required=True, field="claim.claim_type"),
                        _text(spec.get("author_strength")),
                        _text(spec.get("scope")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "claim", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="claim", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Claim: {spec.get('statement')}")
                counts["claims"] += 1

            for spec in leads:
                artifact_id, locator = _source_fields(
                    connection, paper_id, spec, required=True, field="Lead"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO leads(
                        paper_id, type, title, identifier, url, purpose, priority,
                        status, artifact_id, source_locator
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        _text(spec.get("type"), required=True, field="lead.type"),
                        _text(spec.get("title")),
                        _text(spec.get("identifier")),
                        _text(spec.get("url")),
                        _text(spec.get("purpose")),
                        _text(spec.get("priority")),
                        _text(spec.get("status")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                _register_ref(refs, "lead", spec, entity_id)
                _write_change(connection, timestamp=timestamp, entity_type="lead", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Lead: {spec.get('title') or spec.get('identifier')}")
                counts["leads"] += 1

            counts["relations"] = _insert_relations(
                connection, paper_id, refs, relations, timestamp, reason, run_id
            )
            new_depth = _depth(str(paper["read_depth"]), requested_depth)
            connection.execute(
                """
                UPDATE papers
                SET status = 'active', read_depth = ?, reading_status = 'reconstructed',
                    updated_at = ?
                WHERE id = ?
                """,
                (new_depth, timestamp, paper_id),
            )
            _write_change(connection, timestamp=timestamp, entity_type="reading_run", entity_id=str(run_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Completed reconstruction ({requested_depth})")
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

    return {
        "ok": True,
        "paper_id": paper_id,
        "reading_run_id": run_id,
        "pass": "reconstruction",
        "depth": requested_depth,
        "reading_status": "reconstructed",
        "counts": counts,
        "refs": {f"{kind}:{ref}": entity_id for (kind, ref), entity_id in refs.items()},
    }


