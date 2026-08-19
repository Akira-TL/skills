from __future__ import annotations

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
    "reading_runs",
    "methods",
    "experiments",
    "observations",
    "claims",
    "issues",
    "leads",
    "relations",
    "change_log",
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
    return {
        "project_root": str(project_root),
        "database": str(db_path),
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
                "SELECT id, path FROM artifacts ORDER BY id"
            ):
                artifact_path = Path(row["path"])
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

    if not (project_root / "RESEARCH.md").exists():
        warnings.append("项目根目录没有 RESEARCH.md；数据库可用，但不满足完整科研项目 bootstrap 契约。")

    return {
        "ok": not errors,
        "database": str(db_path),
        "errors": errors,
        "warnings": warnings,
    }
