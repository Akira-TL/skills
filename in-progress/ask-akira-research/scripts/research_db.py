from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

from research_db_core import (
    ResearchDbError,
    apply_migrations,
    database_path,
    discover_project_root,
    init_database,
    status,
    validate,
)


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_init(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project, for_init=True)
    emit(init_database(project_root))
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    db_path = database_path(project_root)
    if not db_path.exists():
        raise ResearchDbError("research.sqlite 不存在；新项目请先运行 research-db init。")
    applied = apply_migrations(db_path)
    payload = status(project_root)
    payload["applied_migrations"] = applied
    emit(payload)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project, for_init=True)
    emit(status(project_root))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project, for_init=True)
    payload = validate(project_root)
    emit(payload)
    return 0 if payload["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-db",
        description="ask-akira-research 的项目级 SQLite 管理工具。",
    )
    parser.add_argument(
        "--project",
        help="科研项目根目录；省略时从当前目录向上查找 RESEARCH.md 或 .research。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands: list[tuple[str, str, Callable[[argparse.Namespace], int]]] = [
        ("init", "创建 .research/research.sqlite 并应用全部 migration。", cmd_init),
        ("migrate", "把已有数据库升级到当前 schema。", cmd_migrate),
        ("status", "输出数据库路径、schema 版本和表计数。", cmd_status),
        ("validate", "执行 SQLite、schema、引用、artifact 与阅读状态完整性检查。", cmd_validate),
    ]
    for name, help_text, handler in commands:
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.set_defaults(handler=handler)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (ResearchDbError, sqlite3.DatabaseError, OSError, ValueError) as exc:
        emit({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
