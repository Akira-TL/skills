from __future__ import annotations

import json
from pathlib import Path

from research_db_ops.acquisition import code_data_access_blockers, supplement_access_blockers
from research_db_support.checks import main_text_exposes_code_data_locator

def _check_supplement(connection, run, checks: dict, errors: list[str]) -> None:
    supplement_presence = checks.get("supplement_presence")
    if supplement_presence not in {"present", "none_found", "unclear"}:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 缺少有效 supplement_presence。"
        )
    supplement_status = checks.get("supplement_status")
    if supplement_status == "not_applicable" and supplement_presence != "none_found":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "supplement_status=not_applicable 但 supplement_presence 不是 none_found。"
        )
    if supplement_status == "checked" and supplement_presence != "present":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "supplement_status=checked 但 supplement_presence 不是 present。"
        )
    if supplement_status == "access_limited" and supplement_presence not in {"present", "unclear"}:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "supplement_status=access_limited 但 supplement_presence 不是 present/unclear。"
        )

    supplement_ids = {
        int(row["id"])
        for row in connection.execute(
            """
            SELECT id, kind FROM artifacts
            WHERE paper_id = ? AND created_at <= ?
            """,
            (run["paper_id"], run["completed_at"]),
        )
        if str(row["kind"]).casefold().startswith(("supplement", "supplementary"))
        or str(row["kind"]).casefold() == "reporting_summary"
    }
    if supplement_ids and supplement_presence != "present":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 已登记 supplement artifact，"
            "supplement_presence 必须为 present。"
        )
    if supplement_ids and supplement_status == "not_applicable":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 已登记 supplement artifact，"
            "supplement_status 不能为 not_applicable。"
        )
    if supplement_status == "checked" and not supplement_ids:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 声明 supplement_status=checked，"
            "但没有登记 supplement artifact。"
        )
    if supplement_ids and supplement_status in {"checked", "access_limited"}:
        try:
            checked_artifacts = json.loads(run["artifacts_checked"] or "[]")
        except json.JSONDecodeError:
            checked_artifacts = []
        checked_ids = {
            int(item["id"])
            for item in checked_artifacts
            if isinstance(item, dict) and item.get("id") is not None
        }
        missing_ids = sorted(supplement_ids - checked_ids)
        if missing_ids:
            errors.append(
                f"deep_extraction run {run['id']} ({run['paper_id']}) "
                f"声明 supplement_status={supplement_status}，但 artifacts_checked 未覆盖全部已登记 supplement artifact："
                + ", ".join(str(value) for value in missing_ids)
            )
    if supplement_status == "access_limited":
        raw_attempt_ids = checks.get("supplement_attempt_ids")
        if not isinstance(raw_attempt_ids, list) or not raw_attempt_ids or not all(
            isinstance(value, int) and value > 0 for value in raw_attempt_ids
        ):
            errors.append(
                f"deep_extraction run {run['id']} ({run['paper_id']}) access_limited "
                "缺少有效 supplement_attempt_ids。"
            )
        else:
            blockers = supplement_access_blockers(
                connection, str(run["paper_id"]), raw_attempt_ids
            )
            for blocker in blockers:
                errors.append(
                    f"deep_extraction run {run['id']} ({run['paper_id']}) "
                    f"supplement access provenance 不完整：{blocker}。"
                )

def _check_code_data(project_root: Path, connection, run, checks: dict, errors: list[str]) -> None:
    code_data_presence = checks.get("code_data_presence")
    if code_data_presence not in {"present", "none_found", "unclear"}:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 缺少有效 code_data_presence。"
        )
    code_data_status = checks.get("code_data_status")
    if (
        code_data_presence == "none_found"
        and main_text_exposes_code_data_locator(
            project_root, connection, str(run["paper_id"])
        )
    ):
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 的主文明确暴露代码/数据获取位置，"
            "code_data_presence 不能为 none_found。"
        )
    if code_data_status == "not_applicable" and code_data_presence != "none_found":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "code_data_status=not_applicable 但 code_data_presence 不是 none_found。"
        )
    if code_data_status == "checked" and code_data_presence != "present":
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "code_data_status=checked 但 code_data_presence 不是 present。"
        )
    if code_data_status == "access_limited" and code_data_presence not in {"present", "unclear"}:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) "
            "code_data_status=access_limited 但 code_data_presence 不是 present/unclear。"
        )
    if code_data_status in {"checked", "access_limited"}:
        raw_attempt_ids = checks.get("code_data_attempt_ids")
        if not isinstance(raw_attempt_ids, list) or not raw_attempt_ids or not all(
            isinstance(value, int) and value > 0 for value in raw_attempt_ids
        ):
            errors.append(
                f"deep_extraction run {run['id']} ({run['paper_id']}) "
                f"code_data_status={code_data_status} 缺少有效 code_data_attempt_ids。"
            )
        else:
            blockers = code_data_access_blockers(
                connection,
                str(run["paper_id"]),
                raw_attempt_ids,
                status=str(code_data_status),
            )
            for blocker in blockers:
                errors.append(
                    f"deep_extraction run {run['id']} ({run['paper_id']}) "
                    f"code/data access provenance 不完整：{blocker}。"
                )

def _check_quantitative(connection, run, checks: dict, errors: list[str]) -> None:
    quantitative_present = checks.get("quantitative_results_present")
    if not isinstance(quantitative_present, bool):
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 未声明 quantitative_results_present。"
        )
    elif quantitative_present:
        count = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM observations
                WHERE paper_id = ?
                  AND statistics_json IS NOT NULL
                  AND trim(statistics_json) NOT IN ('', '{}', 'null')
                """,
                (run["paper_id"],),
            ).fetchone()[0]
        )
        if count == 0:
            errors.append(
                f"deep_extraction run {run['id']} ({run['paper_id']}) 声明存在定量结果，"
                "但没有 Observation 保存 statistics_json。"
            )
    elif not checks.get("quantitative_results_reason"):
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 声明无定量结果，"
            "但没有说明 quantitative_results_reason。"
        )

def _check_deep_extraction(project_root: Path, connection, run, checks: dict, errors: list[str]) -> None:
    if checks.get("figures_tables_checked") is not True:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 未确认 figures/tables 检查。"
        )
    if checks.get("quantitative_results_checked") is not True:
        errors.append(
            f"deep_extraction run {run['id']} ({run['paper_id']}) 未确认定量结果检查。"
        )
    for field in ("supplement_status", "code_data_status"):
        value = checks.get(field)
        if value not in {"checked", "not_applicable", "access_limited"}:
            errors.append(
                f"deep_extraction run {run['id']} ({run['paper_id']}) 的 {field} 状态不完整。"
            )
        elif value in {"not_applicable", "access_limited"}:
            reason_field = field.removesuffix("_status") + "_reason"
            if not checks.get(reason_field):
                errors.append(
                    f"deep_extraction run {run['id']} ({run['paper_id']}) 的 "
                    f"{field}={value} 缺少 {reason_field}。"
                )
    _check_supplement(connection, run, checks, errors)
    _check_code_data(project_root, connection, run, checks, errors)
    _check_quantitative(connection, run, checks, errors)

def _check_reconstruction(project_root: Path, connection, errors: list[str]) -> None:
    reconstructed_without_run = connection.execute(
        """
        SELECT p.id FROM papers p
        WHERE p.reading_status IN ('reconstructed', 'extracted')
          AND NOT EXISTS (
            SELECT 1 FROM reading_runs r
            WHERE r.paper_id = p.id
              AND r.pass = 'reconstruction'
              AND r.completed_at IS NOT NULL
          )
        """
    ).fetchall()
    for row in reconstructed_without_run:
        errors.append(f"{row['id']} 标记为 reconstructed/extracted，但缺少完成的 reconstruction run。")

    for run in connection.execute(
        """
        SELECT id, paper_id, depth, completed_at, artifacts_checked, extraction_checks_json
        FROM reading_runs
        WHERE pass = 'reconstruction' AND completed_at IS NOT NULL
        ORDER BY id
        """
    ):
        raw_checks = run["extraction_checks_json"]
        try:
            checks = json.loads(raw_checks) if raw_checks else None
        except json.JSONDecodeError:
            checks = None
        if not isinstance(checks, dict):
            checks = {}
        if checks.get("observation_semantics_checked") is not True:
            errors.append(
                f"reconstruction run {run['id']} ({run['paper_id']}) 缺少完成的 Observation 语义自审。"
            )
        if run["depth"] == "deep_extraction":
            _check_deep_extraction(project_root, connection, run, checks, errors)

def _check_critical(connection, errors: list[str], warnings: list[str]) -> None:
    critical_without_run = connection.execute(
        """
        SELECT p.id FROM papers p
        WHERE p.critical_status = 'critically_reviewed'
          AND NOT EXISTS (
            SELECT 1 FROM reading_runs r
            WHERE r.paper_id = p.id
              AND r.pass = 'critical_audit'
              AND r.completed_at IS NOT NULL
          )
        """
    ).fetchall()
    for row in critical_without_run:
        errors.append(f"{row['id']} 标记为 critically_reviewed，但缺少完成的 critical audit run。")

    for row in connection.execute(
        """
        SELECT c.id, c.paper_id
        FROM reading_runs c
        WHERE c.pass = 'critical_audit'
          AND c.depth = 'deep_extraction'
          AND c.completed_at IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM reading_runs r
            WHERE r.paper_id = c.paper_id
              AND r.pass = 'reconstruction'
              AND r.depth = 'deep_extraction'
              AND r.completed_at IS NOT NULL
          )
        """
    ):
        errors.append(
            f"critical audit run {row['id']} ({row['paper_id']}) 标为 deep_extraction，"
            "但没有对应的 deep_extraction Reconstruction。"
        )

    reviewed_without_issue = connection.execute(
        """
        SELECT p.id FROM papers p
        WHERE p.critical_status = 'critically_reviewed'
          AND NOT EXISTS (SELECT 1 FROM issues i WHERE i.paper_id = p.id)
        """
    ).fetchall()
    for row in reviewed_without_issue:
        warnings.append(f"{row['id']} 已 critically_reviewed，但没有记录 Issue；请确认这是有意结果。")

def _check_paper_identity(connection, errors: list[str]) -> None:
    for row in connection.execute(
        "SELECT id, doi, pmid, canonical_identity FROM papers ORDER BY id"
    ):
        doi = str(row["doi"]).strip().lower() if row["doi"] else None
        pmid = str(row["pmid"]).strip() if row["pmid"] else None
        expected_identity = f"doi:{doi}" if doi else (f"pmid:{pmid}" if pmid else None)
        canonical = (
            str(row["canonical_identity"]).strip().lower()
            if row["canonical_identity"]
            else None
        )
        if expected_identity and canonical != expected_identity.lower():
            errors.append(
                f"{row['id']} canonical_identity={row['canonical_identity']!r} "
                f"与稳定论文身份 {expected_identity!r} 不一致。"
            )

def check_reading(project_root: Path, connection, errors: list[str], warnings: list[str]) -> None:
    _check_reconstruction(project_root, connection, errors)
    _check_critical(connection, errors, warnings)
    _check_paper_identity(connection, errors)
