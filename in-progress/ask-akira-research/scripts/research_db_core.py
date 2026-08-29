from __future__ import annotations

import json
import re
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


class ResearchDbError(RuntimeError):
    pass


def main_text_exposes_code_data_locator(
    project_root: Path, connection: sqlite3.Connection, paper_id: str
) -> bool:
    """Detect a narrow, explicit data/code locator in machine-readable main text."""
    rows = connection.execute(
        "SELECT path FROM artifacts WHERE paper_id = ? AND kind = 'main_text' ORDER BY id",
        (paper_id,),
    ).fetchall()
    heading_patterns = (
        "availability of data and materials",
        "data availability",
        "code availability",
        "availability of data",
    )
    for row in rows:
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = project_root / path
        if path.suffix.casefold() not in {".xml", ".html", ".htm", ".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text[:6_000_000].casefold()
        for heading in heading_patterns:
            for match in re.finditer(re.escape(heading), lowered):
                window = lowered[match.start() : match.start() + 5000]
                has_locator = bool(
                    re.search(r"https?://|href\s*=|doi:\s*10\.|accession|repository", window)
                )
                has_availability_signal = any(
                    phrase in window
                    for phrase in (
                        "available at",
                        "available from",
                        "publicly available",
                        "freely available",
                        "deposited",
                        "repository",
                        "accession",
                    )
                )
                if has_locator and has_availability_signal:
                    return True
    return False


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
    from research_db_validation import validate as validate_database

    return validate_database(project_root)
