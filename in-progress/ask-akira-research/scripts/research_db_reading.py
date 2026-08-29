from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import research_db_support.knowledge as knowledge
from research_db_support.checks import main_text_exposes_code_data_locator
from research_db_support.storage import ResearchDbError, connect, database_path
from research_db_ops.acquisition import code_data_access_blockers, supplement_access_blockers


DEEP_EXTRACTION_STATUSES = {"checked", "not_applicable", "access_limited"}
SUPPLEMENT_PRESENCE = {"present", "none_found", "unclear"}
CODE_DATA_PRESENCE = {"present", "none_found", "unclear"}
SUPPLEMENT_ARTIFACT_PREFIXES = ("supplement", "supplementary")


def _extraction_checks(
    bundle: dict[str, Any],
    *,
    depth: str,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    raw = bundle.get("extraction_checks")
    if not isinstance(raw, dict):
        raise ResearchDbError("Reconstruction 必须提供 extraction_checks object。")
    checks = dict(raw)
    if checks.get("observation_semantics_checked") is not True:
        raise ResearchDbError(
            "extraction_checks.observation_semantics_checked 必须为 true；"
            "写入前逐条确认 Observation 只包含数据直接显示的结果。"
        )
    if depth != "deep_extraction":
        return checks

    for field in ("figures_tables_checked", "quantitative_results_checked"):
        if checks.get(field) is not True:
            raise ResearchDbError(f"deep_extraction 要求 extraction_checks.{field}=true。")
    for field in ("supplement_status", "code_data_status"):
        value = checks.get(field)
        if value not in DEEP_EXTRACTION_STATUSES:
            raise ResearchDbError(
                f"deep_extraction 要求 extraction_checks.{field} 为："
                + ", ".join(sorted(DEEP_EXTRACTION_STATUSES))
            )
        if value in {"not_applicable", "access_limited"}:
            reason_field = field.removesuffix("_status") + "_reason"
            if not knowledge.text(checks.get(reason_field)):
                raise ResearchDbError(
                    f"deep_extraction 的 {field}={value} 时必须说明 extraction_checks.{reason_field}。"
                )

    supplement_presence = checks.get("supplement_presence")
    if supplement_presence not in SUPPLEMENT_PRESENCE:
        raise ResearchDbError(
            "deep_extraction 要求 extraction_checks.supplement_presence 为："
            + ", ".join(sorted(SUPPLEMENT_PRESENCE))
        )
    supplement_status = checks.get("supplement_status")
    if supplement_status == "not_applicable" and supplement_presence != "none_found":
        raise ResearchDbError(
            "supplement_status=not_applicable 只允许 supplement_presence=none_found。"
        )
    if supplement_status == "checked" and supplement_presence != "present":
        raise ResearchDbError(
            "supplement_status=checked 要求 supplement_presence=present。"
        )
    if supplement_status == "access_limited" and supplement_presence not in {"present", "unclear"}:
        raise ResearchDbError(
            "supplement_status=access_limited 要求 supplement_presence 为 present 或 unclear。"
        )
    if supplement_status == "access_limited":
        attempt_ids = checks.get("supplement_attempt_ids")
        if not isinstance(attempt_ids, list) or not attempt_ids or not all(
            isinstance(value, int) and value > 0 for value in attempt_ids
        ):
            raise ResearchDbError(
                "supplement_status=access_limited 必须提供非空整数数组 supplement_attempt_ids。"
            )

    code_data_presence = checks.get("code_data_presence")
    if code_data_presence not in CODE_DATA_PRESENCE:
        raise ResearchDbError(
            "deep_extraction 要求 extraction_checks.code_data_presence 为："
            + ", ".join(sorted(CODE_DATA_PRESENCE))
        )
    code_data_status = checks.get("code_data_status")
    if code_data_status == "not_applicable" and code_data_presence != "none_found":
        raise ResearchDbError(
            "code_data_status=not_applicable 只允许 code_data_presence=none_found。"
        )
    if code_data_status == "checked" and code_data_presence != "present":
        raise ResearchDbError(
            "code_data_status=checked 要求 code_data_presence=present。"
        )
    if code_data_status == "access_limited" and code_data_presence not in {"present", "unclear"}:
        raise ResearchDbError(
            "code_data_status=access_limited 要求 code_data_presence 为 present 或 unclear。"
        )
    if code_data_status in {"checked", "access_limited"}:
        attempt_ids = checks.get("code_data_attempt_ids")
        if not isinstance(attempt_ids, list) or not attempt_ids or not all(
            isinstance(value, int) and value > 0 for value in attempt_ids
        ):
            raise ResearchDbError(
                f"code_data_status={code_data_status} 必须提供非空整数数组 code_data_attempt_ids。"
            )

    present = checks.get("quantitative_results_present")
    if not isinstance(present, bool):
        raise ResearchDbError(
            "deep_extraction 要求 extraction_checks.quantitative_results_present 为 boolean。"
        )
    has_statistics = any(
        isinstance(item.get("statistics"), dict) and bool(item.get("statistics"))
        for item in observations
    )
    if present and not has_statistics:
        raise ResearchDbError(
            "quantitative_results_present=true 时至少一个 Observation 必须保存非空 statistics。"
        )
    if not present and not knowledge.text(checks.get("quantitative_results_reason")):
        raise ResearchDbError(
            "quantitative_results_present=false 时必须说明 quantitative_results_reason。"
        )
    return checks


def _validate_deep_artifact_checks(
    project_root: Path,
    connection: Any,
    paper_id: str,
    checked: list[dict[str, Any]],
    checks: dict[str, Any],
) -> None:
    supplement_rows = connection.execute(
        "SELECT id, kind FROM artifacts WHERE paper_id = ? ORDER BY id",
        (paper_id,),
    ).fetchall()
    supplement_ids = {
        int(row["id"])
        for row in supplement_rows
        if str(row["kind"]).casefold().startswith(SUPPLEMENT_ARTIFACT_PREFIXES)
        or str(row["kind"]).casefold() == "reporting_summary"
    }
    supplement_status = checks.get("supplement_status")
    supplement_presence = checks.get("supplement_presence")
    if supplement_ids and supplement_presence != "present":
        raise ResearchDbError(
            "deep_extraction 已登记 supplement artifact，supplement_presence 必须为 present。"
        )
    if supplement_ids and supplement_status == "not_applicable":
        raise ResearchDbError(
            "deep_extraction 已登记 supplement artifact，supplement_status 不能为 not_applicable；"
            "至少检查已取得附件并标记 checked，或明确记录真实的 access_limited 情形。"
        )
    if supplement_status == "checked" and not supplement_ids:
        raise ResearchDbError(
            "deep_extraction 声明 supplement_status=checked，但没有登记任何 supplement artifact。"
        )
    if supplement_ids and supplement_status in {"checked", "access_limited"}:
        checked_ids = {int(item["id"]) for item in checked}
        missing_ids = sorted(supplement_ids - checked_ids)
        if missing_ids:
            raise ResearchDbError(
                f"deep_extraction 声明 supplement_status={supplement_status}，"
                "但 artifacts_checked 未覆盖全部已登记 supplement artifact："
                + ", ".join(str(value) for value in missing_ids)
            )

    if supplement_status == "access_limited":
        attempt_ids = list(dict.fromkeys(checks.get("supplement_attempt_ids", [])))
        blockers = supplement_access_blockers(connection, paper_id, attempt_ids)
        if blockers:
            raise ResearchDbError(
                "supplement_status=access_limited 的 Acquisition Attempt provenance 未闭合："
                + ", ".join(blockers)
            )

    code_data_status = checks.get("code_data_status")
    code_data_presence = checks.get("code_data_presence")
    if (
        code_data_presence == "none_found"
        and main_text_exposes_code_data_locator(project_root, connection, paper_id)
    ):
        raise ResearchDbError(
            "deep_extraction 的主文明确暴露代码/数据获取位置，code_data_presence 不能为 none_found。"
        )
    if code_data_status in {"checked", "access_limited"}:
        attempt_ids = list(dict.fromkeys(checks.get("code_data_attempt_ids", [])))
        blockers = code_data_access_blockers(
            connection, paper_id, attempt_ids, status=str(code_data_status)
        )
        if blockers:
            raise ResearchDbError(
                f"code_data_status={code_data_status} 的 Acquisition Attempt provenance 未闭合："
                + ", ".join(blockers)
            )


def ingest_reading(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
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
    reason = knowledge.text(bundle.get("reason")) or "Pass 1 Reconstruction"

    methods = knowledge.array(bundle, "methods")
    experiments = knowledge.array(bundle, "experiments")
    observations = knowledge.array(bundle, "observations")
    claims = knowledge.array(bundle, "claims")
    leads = knowledge.array(bundle, "leads")
    relations = knowledge.array(bundle, "relations")
    if not any((methods, experiments, observations, claims, leads)):
        raise ResearchDbError("Reconstruction bundle 至少需要一个知识单元。")
    extraction_checks = _extraction_checks(
        bundle,
        depth=requested_depth,
        observations=observations,
    )

    refs: dict[tuple[str, str], str] = {}
    counts = {name: 0 for name in ("methods", "experiments", "observations", "claims", "leads", "relations")}
    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            paper = knowledge.paper(connection, paper_id)
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
            checked = knowledge.checked_artifacts(connection, paper_id, bundle.get("artifacts_checked"))
            if requested_depth == "deep_extraction":
                _validate_deep_artifact_checks(
                    project_root, connection, paper_id, checked, extraction_checks
                )
            run_cursor = connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked, notes, extraction_checks_json
                ) VALUES (?, 'reconstruction', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    requested_depth,
                    started_at,
                    completed_at,
                    json.dumps(checked, ensure_ascii=False),
                    json.dumps(sections, ensure_ascii=False),
                    knowledge.text(bundle.get("notes")),
                    json.dumps(extraction_checks, ensure_ascii=False, sort_keys=True),
                ),
            )
            run_id = int(run_cursor.lastrowid)

            for spec in methods:
                artifact_id, locator = knowledge.source_fields(
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
                        knowledge.text(spec.get("name"), required=True, field="method.name"),
                        knowledge.text(spec.get("purpose")),
                        knowledge.text(spec.get("description")),
                        knowledge.json_text(spec.get("parameters")),
                        knowledge.json_text(spec.get("materials")),
                        knowledge.json_text(spec.get("software")),
                        knowledge.text(spec.get("reusable_notes")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "method", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="method", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Method: {spec.get('name')}")
                counts["methods"] += 1

            for spec in experiments:
                artifact_id, locator = knowledge.source_fields(
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
                        knowledge.text(spec.get("question")),
                        knowledge.text(spec.get("design")),
                        knowledge.text(spec.get("samples")),
                        knowledge.json_text(spec.get("groups")),
                        knowledge.text(spec.get("controls")),
                        knowledge.json_text(spec.get("variables")),
                        knowledge.text(spec.get("analysis")),
                        knowledge.text(spec.get("result_summary")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "experiment", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="experiment", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Experiment: {spec.get('question') or spec.get('design')}")
                counts["experiments"] += 1

            for spec in observations:
                artifact_id, locator = knowledge.source_fields(
                    connection, paper_id, spec, required=True, field="Observation"
                )
                experiment_id = None
                if spec.get("experiment_ref") is not None:
                    key = ("experiment", knowledge.text(spec.get("experiment_ref"), required=True, field="observation.experiment_ref"))
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
                        knowledge.text(spec.get("statement"), required=True, field="observation.statement"),
                        knowledge.text(spec.get("effect")),
                        knowledge.json_text(spec.get("statistics")),
                        knowledge.text(spec.get("scope")),
                        knowledge.text(spec.get("certainty")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "observation", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="observation", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Observation: {spec.get('statement')}")
                counts["observations"] += 1

            for spec in claims:
                artifact_id, locator = knowledge.source_fields(
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
                        knowledge.text(spec.get("statement"), required=True, field="claim.statement"),
                        knowledge.text(spec.get("claim_type"), required=True, field="claim.claim_type"),
                        knowledge.text(spec.get("author_strength")),
                        knowledge.text(spec.get("scope")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "claim", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="claim", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Claim: {spec.get('statement')}")
                counts["claims"] += 1

            for spec in leads:
                artifact_id, locator = knowledge.source_fields(
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
                        knowledge.text(spec.get("type"), required=True, field="lead.type"),
                        knowledge.text(spec.get("title")),
                        knowledge.text(spec.get("identifier")),
                        knowledge.text(spec.get("url")),
                        knowledge.text(spec.get("purpose")),
                        knowledge.text(spec.get("priority")),
                        knowledge.text(spec.get("status")),
                        artifact_id,
                        locator,
                    ),
                )
                entity_id = int(cursor.lastrowid)
                knowledge.register_ref(refs, "lead", spec, entity_id)
                knowledge.write_change(connection, timestamp=timestamp, entity_type="lead", entity_id=str(entity_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Lead: {spec.get('title') or spec.get('identifier')}")
                counts["leads"] += 1

            counts["relations"] = knowledge.insert_relations(
                connection, paper_id, refs, relations, timestamp, reason, run_id
            )
            new_depth = knowledge.depth(str(paper["read_depth"]), requested_depth)
            connection.execute(
                """
                UPDATE papers
                SET status = 'active', read_depth = ?, reading_status = 'reconstructed',
                    updated_at = ?
                WHERE id = ?
                """,
                (new_depth, timestamp, paper_id),
            )
            knowledge.write_change(connection, timestamp=timestamp, entity_type="reading_run", entity_id=str(run_id), paper_id=paper_id, reason=reason, run_id=run_id, summary=f"Completed reconstruction ({requested_depth})")
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


