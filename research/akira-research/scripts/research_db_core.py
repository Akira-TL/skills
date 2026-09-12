from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.checks import (
    main_text_exposes_code_data_locator,
    source_locator_is_specific as _source_locator_is_specific,
)
from research_db_support.schema import (
    ENTITY_TABLES,
    MIGRATION_DIR,
    REQUIRED_TABLES,
    Migration,
    apply_migrations,
    entity_exists as _entity_exists,
    latest_version,
    list_migrations,
)
from research_db_support.storage import (
    ResearchDbError,
    connect,
    current_version,
    database_path,
    read_meta_version,
    table_names,
)


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


GITIGNORE_BEGIN = "# BEGIN akira-research managed ignores"
GITIGNORE_END = "# END akira-research managed ignores"
GITIGNORE_BODY = """# Language/runtime caches
__pycache__/
*.py[cod]
.Rhistory
.RData

# Machine/raw research artifacts and disposable execution outputs
.research/artifacts/
.research/cache/
.research/tmp/
.research/analysis/**/outputs/
.research/analysis/**/logs/

# Human convenience copies and reproducible generated figures
literature/papers/*.pdf
analysis/**/figures/*.png
analysis/**/figures/*.jpg
analysis/**/figures/*.jpeg
analysis/**/figures/*.tif
analysis/**/figures/*.tiff
analysis/**/figures/*.pdf
analysis/**/figures/*.svg
"""


def ensure_research_gitignore(project_root: Path) -> bool:
    path = project_root / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if GITIGNORE_BEGIN in existing and GITIGNORE_END in existing:
        return False
    block = f"{GITIGNORE_BEGIN}\n{GITIGNORE_BODY}{GITIGNORE_END}\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    if existing:
        existing += "\n"
    path.write_text(existing + block, encoding="utf-8")
    return True


def init_database(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    if db_path.exists():
        raise ResearchDbError(f"数据库已存在：{db_path}")
    applied = apply_migrations(db_path)
    bundle_dir = db_path.parent / "bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    gitignore_updated = ensure_research_gitignore(project_root)
    return {
        "project_root": str(project_root),
        "database": str(db_path),
        "bundle_directory": str(bundle_dir),
        "created": True,
        "gitignore_updated": gitignore_updated,
        "applied_migrations": applied,
        "schema_version": latest_version(),
    }


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


def validate(project_root: Path) -> dict[str, Any]:
    from research_db_validation import validate as validate_database

    return validate_database(project_root)
