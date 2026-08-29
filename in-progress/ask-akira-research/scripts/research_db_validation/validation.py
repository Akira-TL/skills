from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.schema import REQUIRED_TABLES, latest_version
from research_db_support.storage import connect, current_version, database_path, read_meta_version, table_names
from .acquisition import check_acquisition
from .artifacts import check_artifacts
from .knowledge import check_knowledge
from .project import check_project
from .reading import check_reading


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
            check_reading(project_root, connection, errors, warnings)
            check_acquisition(connection, errors)
            check_artifacts(project_root, connection, errors, warnings)
            check_project(project_root, connection, errors)
            check_knowledge(connection, errors)

    if not (project_root / "RESEARCH.md").exists():
        warnings.append("项目根目录没有 RESEARCH.md；数据库可用，但不满足完整科研项目 bootstrap 契约。")

    return {
        "ok": not errors,
        "database": str(db_path),
        "errors": errors,
        "warnings": warnings,
    }
