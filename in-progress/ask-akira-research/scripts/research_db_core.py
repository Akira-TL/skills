from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MIGRATION_DIR = Path(__file__).resolve().parent.parent / "migrations"
REQUIRED_TABLES = {
    "meta",
    "papers",
    "artifacts",
    "search_runs",
    "candidates",
    "search_run_candidates",
    "reading_runs",
    "methods",
    "experiments",
    "observations",
    "claims",
    "issues",
    "leads",
    "relations",
    "change_log",
    "acquisition_attempts",
}
ENTITY_TABLES = {
    "paper": "papers",
    "artifact": "artifacts",
    "search_run": "search_runs",
    "candidate": "candidates",
    "reading_run": "reading_runs",
    "method": "methods",
    "experiment": "experiments",
    "observation": "observations",
    "claim": "claims",
    "issue": "issues",
    "lead": "leads",
}


@dataclass(frozen=True)
class Migration:
    version: int
    path: Path


class ResearchDbError(RuntimeError):
    pass


def _source_locator_is_specific(value: object) -> bool:
    if value is None:
        return False
    normalized = " ".join(str(value).strip().casefold().split())
    if not normalized:
        return False
    generic = {
        "abstract",
        "introduction",
        "methods",
        "materials and methods",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "main text",
        "supplement",
        "supplementary material",
        "supplementary materials",
        "supplementary information",
    }
    return normalized not in generic


def discover_project_root(project: str | None, *, for_init: bool = False) -> Path:
    if project:
        return Path(project).expanduser().resolve()

    start = Path.cwd().resolve()
    for directory in (start, *start.parents):
        if (directory / ".research" / "research.sqlite").exists():
            return directory
        if (directory / "RESEARCH.md").exists():
            return directory

    if for_init:
        return start
    raise ResearchDbError(
        "无法定位科研项目；请在包含 RESEARCH.md/.research 的目录内运行，或传入 --project。"
    )


def database_path(project_root: Path) -> Path:
    return project_root / ".research" / "research.sqlite"


def list_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(MIGRATION_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        migrations.append(Migration(version=int(path.name[:3]), path=path))

    if not migrations:
        raise ResearchDbError(f"没有找到 migration：{MIGRATION_DIR}")

    expected = list(range(1, migrations[-1].version + 1))
    actual = [migration.version for migration in migrations]
    if actual != expected:
        raise ResearchDbError(f"migration 版本不连续：{actual}")
    return migrations


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def current_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def latest_version() -> int:
    return list_migrations()[-1].version


def apply_migrations(db_path: Path) -> list[int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migrations = list_migrations()
    applied: list[int] = []

    with connect(db_path) as connection:
        version = current_version(connection)
        if version > migrations[-1].version:
            raise ResearchDbError(
                f"数据库 schema v{version} 高于当前脚本支持的 v{migrations[-1].version}。"
            )

        for migration in migrations:
            if migration.version <= version:
                continue
            if migration.version != version + 1:
                raise ResearchDbError(
                    f"migration 断层：当前 v{version}，下一文件为 v{migration.version}。"
                )

            sql = migration.path.read_text(encoding="utf-8")
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{sql}\n"
                f"PRAGMA user_version = {migration.version};\n"
                "INSERT INTO meta(key, value) VALUES('schema_version', "
                f"'{migration.version}') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;\n"
                "COMMIT;"
            )
            try:
                connection.executescript(script)
            except sqlite3.DatabaseError:
                if connection.in_transaction:
                    connection.rollback()
                raise

            version = migration.version
            applied.append(version)

    return applied


def init_database(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    if db_path.exists():
        raise ResearchDbError(f"数据库已存在：{db_path}")
    applied = apply_migrations(db_path)
    bundle_dir = db_path.parent / "bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return {
        "project_root": str(project_root),
        "database": str(db_path),
        "bundle_directory": str(bundle_dir),
        "created": True,
        "applied_migrations": applied,
        "schema_version": latest_version(),
    }


def read_meta_version(connection: sqlite3.Connection) -> int | None:
    try:
        row = connection.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return int(row["value"]) if row else None


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row["name"] for row in rows}


def status(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    result: dict[str, Any] = {
        "project_root": str(project_root),
        "database": str(db_path),
        "exists": db_path.exists(),
        "latest_schema_version": latest_version(),
        "research_md_exists": (project_root / "RESEARCH.md").exists(),
    }
    if not db_path.exists():
        return result

    with connect(db_path) as connection:
        version = current_version(connection)
        counts: dict[str, int] = {}
        existing = table_names(connection)
        for table in sorted(REQUIRED_TABLES & existing):
            counts[table] = int(
                connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
        result.update(
            {
                "schema_version": version,
                "meta_schema_version": read_meta_version(connection),
                "migration_needed": version < latest_version(),
                "tables": counts,
            }
        )
    return result


def _entity_exists(connection: sqlite3.Connection, entity_type: str, entity_id: str) -> bool:
    table = ENTITY_TABLES.get(entity_type)
    if table is None:
        return False
    row = connection.execute(
        f'SELECT 1 FROM "{table}" WHERE CAST(id AS TEXT) = ? LIMIT 1', (entity_id,)
    ).fetchone()
    return row is not None


def validate(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    errors: list[str] = []
    warnings: list[str] = []

    if not db_path.exists():
        return {
            "ok": False,
            "database": str(db_path),
            "errors": ["research.sqlite 不存在；先运行 research-db init。"],
            "warnings": [],
        }

    with connect(db_path) as connection:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        if quick_check != "ok":
            errors.append(f"SQLite quick_check 失败：{quick_check}")

        fk_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_rows:
            errors.append(f"存在 {len(fk_rows)} 个 foreign key 错误。")

        version = current_version(connection)
        supported = latest_version()
        meta_version = read_meta_version(connection)
        if version != supported:
            errors.append(f"schema version 为 v{version}，当前脚本要求 v{supported}。")
        if meta_version != version:
            errors.append(
                f"meta.schema_version={meta_version!r} 与 PRAGMA user_version={version} 不一致。"
            )

        existing_tables = table_names(connection)
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)
        if missing_tables:
            errors.append(f"缺少数据表：{', '.join(missing_tables)}")

        if not errors:
            from research_db_ops.acquisition import supplement_access_blockers

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
                SELECT id, paper_id, depth, artifacts_checked, extraction_checks_json
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
                            "SELECT id, kind FROM artifacts WHERE paper_id = ?",
                            (run["paper_id"],),
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

            from research_db_ops.acquisition import unavailable_candidate_blockers

            for attempt in connection.execute(
                """
                SELECT id, candidate_id, paper_id, target_kind, validity_status,
                       superseded_by_attempt_id, supersession_reason
                FROM acquisition_attempts ORDER BY id
                """
            ):
                attempt_id = int(attempt["id"])
                validity = attempt["validity_status"]
                superseded_by = attempt["superseded_by_attempt_id"]
                reason = attempt["supersession_reason"]
                if validity == "active" and (superseded_by is not None or reason):
                    errors.append(
                        f"acquisition attempt {attempt_id} 仍为 active，但携带 supersession metadata。"
                    )
                if validity == "superseded":
                    if superseded_by is None or not (reason and str(reason).strip()):
                        errors.append(
                            f"acquisition attempt {attempt_id} 标记 superseded，但缺少 superseded_by_attempt_id/supersession_reason。"
                        )
                        continue
                    replacement = connection.execute(
                        """
                        SELECT id, candidate_id, paper_id, target_kind, validity_status
                        FROM acquisition_attempts WHERE id = ?
                        """,
                        (superseded_by,),
                    ).fetchone()
                    if replacement is None:
                        errors.append(
                            f"acquisition attempt {attempt_id} 指向不存在的 superseding attempt {superseded_by}。"
                        )
                    else:
                        if int(replacement["id"]) == attempt_id:
                            errors.append(
                                f"acquisition attempt {attempt_id} 不能 supersede 自身。"
                            )
                        if int(replacement["id"]) <= attempt_id:
                            errors.append(
                                f"acquisition attempt {attempt_id} 的 superseding attempt {superseded_by} 必须是后续新记录。"
                            )
                        if replacement["target_kind"] != attempt["target_kind"]:
                            errors.append(
                                f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} target_kind 不一致。"
                            )
                        if attempt["candidate_id"] is not None and replacement["candidate_id"] != attempt["candidate_id"]:
                            errors.append(
                                f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} Candidate 不一致。"
                            )
                        if attempt["paper_id"] is not None and replacement["paper_id"] != attempt["paper_id"]:
                            errors.append(
                                f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} Paper 不一致。"
                            )

            for row in connection.execute(
                """
                SELECT id, identity_status, relevance_status, exclusion_reason,
                       acquisition_status, paper_id, doi, pmid
                FROM candidates ORDER BY id
                """
            ):
                candidate_id = int(row["id"])
                doi = str(row["doi"]).strip().lower() if row["doi"] else None
                pmid = str(row["pmid"]).strip() if row["pmid"] else None
                if row["relevance_status"] == "excluded" and not (
                    row["exclusion_reason"] and str(row["exclusion_reason"]).strip()
                ):
                    errors.append(
                        f"candidate {candidate_id} 标记为 excluded，但缺少 exclusion_reason。"
                    )
                if row["acquisition_status"] == "unavailable":
                    for blocker in unavailable_candidate_blockers(connection, row):
                        errors.append(
                            f"candidate {candidate_id} unavailable provenance 不完整：{blocker['reason']}。"
                        )
                if row["acquisition_status"] == "acquired" and not row["paper_id"]:
                    errors.append(
                        f"candidate {candidate_id} 标记为 acquired，但没有关联 Paper。"
                    )
                if row["paper_id"] and row["acquisition_status"] != "acquired":
                    errors.append(
                        f"candidate {candidate_id} 已关联 {row['paper_id']}，但 acquisition_status 不是 acquired。"
                    )
                if row["identity_status"] == "resolved" and not (doi or pmid or row["paper_id"]):
                    errors.append(
                        f"candidate {candidate_id} 标记为 resolved，但没有 DOI/PMID/Paper identity。"
                    )
                if row["identity_status"] == "unresolved" and (doi or pmid or row["paper_id"]):
                    errors.append(
                        f"candidate {candidate_id} 已有稳定身份，但 identity_status 仍为 unresolved。"
                    )
                if row["paper_id"]:
                    paper = connection.execute(
                        "SELECT doi, pmid FROM papers WHERE id = ?", (row["paper_id"],)
                    ).fetchone()
                    if paper is not None:
                        paper_doi = str(paper["doi"]).strip().lower() if paper["doi"] else None
                        paper_pmid = str(paper["pmid"]).strip() if paper["pmid"] else None
                        if doi and paper_doi and doi != paper_doi:
                            errors.append(
                                f"candidate {candidate_id} DOI 与关联 Paper {row['paper_id']} 不一致。"
                            )
                        if pmid and paper_pmid and pmid != paper_pmid:
                            errors.append(
                                f"candidate {candidate_id} PMID 与关联 Paper {row['paper_id']} 不一致。"
                            )

            for field, expression, where in (
                ("DOI", "lower(doi)", "doi IS NOT NULL AND trim(doi) <> ''"),
                ("PMID", "pmid", "pmid IS NOT NULL AND trim(pmid) <> ''"),
            ):
                duplicates = connection.execute(
                    f"SELECT {expression} AS identity, GROUP_CONCAT(id) AS ids "
                    f"FROM candidates WHERE {where} GROUP BY {expression} HAVING COUNT(*) > 1"
                ).fetchall()
                for duplicate in duplicates:
                    errors.append(
                        f"Candidate 存在重复稳定身份 {field}={duplicate['identity']!r}："
                        f"{duplicate['ids']}；请使用 merge-candidates 合并。"
                    )

            for row in connection.execute(
                "SELECT id, kind, path, content_type FROM artifacts ORDER BY id"
            ):
                stored_path = Path(row["path"])
                if row["kind"] == "main_text" and not stored_path.suffix:
                    errors.append(
                        f"artifact {row['id']} 的 canonical main_text 路径缺少文件扩展名：{row['path']}"
                    )
                artifact_path = stored_path
                if not artifact_path.is_absolute():
                    artifact_path = project_root / artifact_path
                if not artifact_path.exists():
                    errors.append(f"artifact {row['id']} 文件不存在：{artifact_path}")

            for row in connection.execute(
                "SELECT id, sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
            ):
                sidecar_path = Path(row["sidecar_path"])
                if not sidecar_path.is_absolute():
                    sidecar_path = project_root / sidecar_path
                if not sidecar_path.exists():
                    warnings.append(f"{row['id']} 的 sidecar 不存在：{sidecar_path}")

            for row in connection.execute(
                "SELECT id, subject_type, subject_id, object_type, object_id FROM relations"
            ):
                if row["subject_type"] not in ENTITY_TABLES:
                    errors.append(f"relation {row['id']} 使用未知 subject_type={row['subject_type']!r}。")
                elif not _entity_exists(connection, row["subject_type"], row["subject_id"]):
                    errors.append(f"relation {row['id']} 的 subject 不存在。")
                if row["object_type"] not in ENTITY_TABLES:
                    errors.append(f"relation {row['id']} 使用未知 object_type={row['object_type']!r}。")
                elif not _entity_exists(connection, row["object_type"], row["object_id"]):
                    errors.append(f"relation {row['id']} 的 object 不存在。")

            for row in connection.execute(
                "SELECT id, target_type, target_id FROM issues WHERE target_type IS NOT NULL OR target_id IS NOT NULL"
            ):
                if not row["target_type"] or not row["target_id"]:
                    errors.append(f"issue {row['id']} 的 target_type/target_id 必须同时存在。")
                    continue
                if row["target_type"] not in ENTITY_TABLES:
                    errors.append(f"issue {row['id']} 使用未知 target_type={row['target_type']!r}。")
                elif not _entity_exists(connection, row["target_type"], row["target_id"]):
                    errors.append(f"issue {row['id']} 指向不存在的 target。")

            for row in connection.execute(
                "SELECT id, basis, basis_rationale FROM issues ORDER BY id"
            ):
                if not row["basis_rationale"] or not str(row["basis_rationale"]).strip():
                    errors.append(
                        f"issue {row['id']} 缺少 basis_rationale；无法审计 basis={row['basis']!r} 的证据状态判断。"
                    )

            not_reported_without_locator = connection.execute(
                """
                SELECT id FROM issues
                WHERE basis = 'not_reported'
                  AND artifact_id IS NULL
                  AND (source_locator IS NULL OR trim(source_locator) = '')
                """
            ).fetchall()
            for row in not_reported_without_locator:
                errors.append(f"issue {row['id']} 为 not_reported，但没有 artifact/source locator。")

            for entity, table in (
                ("method", "methods"),
                ("experiment", "experiments"),
                ("observation", "observations"),
                ("claim", "claims"),
                ("issue", "issues"),
                ("lead", "leads"),
            ):
                for row in connection.execute(
                    f"SELECT id, paper_id, source_locator FROM {table} ORDER BY id"
                ):
                    if not _source_locator_is_specific(row["source_locator"]):
                        errors.append(
                            f"{entity} {row['id']} ({row['paper_id']}) 的 source_locator="
                            f"{row['source_locator']!r} 过于模糊；需要具体 subsection/page/figure/table/supplement 定位。"
                        )

    if not (project_root / "RESEARCH.md").exists():
        warnings.append("项目根目录没有 RESEARCH.md；数据库可用，但不满足完整科研项目 bootstrap 契约。")

    return {
        "ok": not errors,
        "database": str(db_path),
        "errors": errors,
        "warnings": warnings,
    }
