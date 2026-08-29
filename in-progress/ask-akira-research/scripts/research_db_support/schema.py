from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from research_db_support.storage import ResearchDbError, connect, current_version


MIGRATION_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
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
    "datasets",
    "dataset_artifacts",
    "analysis_runs",
    "analysis_inputs",
    "analysis_dataset_artifact_timing",
    "analysis_artifacts",
    "analysis_amendments",
    "project_observations",
    "hypothesis_sets",
    "research_designs",
    "hypothesis_evaluations",
    "communication_products",
    "communication_artifacts",
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


def list_migrations() -> list[Migration]:
    migrations = [
        Migration(version=int(path.name[:3]), path=path)
        for path in sorted(MIGRATION_DIR.rglob("[0-9][0-9][0-9]_*.sql"))
    ]
    if not migrations:
        raise ResearchDbError(f"没有找到 migration：{MIGRATION_DIR}")

    expected = list(range(1, migrations[-1].version + 1))
    actual = [migration.version for migration in migrations]
    if actual != expected:
        raise ResearchDbError(f"migration 版本不连续：{actual}")
    return migrations


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


def entity_exists(connection: sqlite3.Connection, entity_type: str, entity_id: str) -> bool:
    table = ENTITY_TABLES.get(entity_type)
    if table is None:
        return False
    row = connection.execute(
        f'SELECT 1 FROM "{table}" WHERE CAST(id AS TEXT) = ? LIMIT 1', (entity_id,)
    ).fetchone()
    return row is not None
