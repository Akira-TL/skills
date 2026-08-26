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
from research_db_critical import ingest_critical
from research_db_discovery import (
    list_candidates,
    list_search_runs,
    record_search_run,
    update_candidate,
)
from research_db_ingest import PaperIngestBundle, ingest_paper
from research_db_query import evidence_packet
from research_db_reading import ingest_reading


BUNDLE_DEFAULTS = {
    "record-search": "search.json",
    "update-candidate": "candidate-update.json",
    "ingest-paper": "paper.json",
    "ingest-reading": "reconstruction.json",
    "ingest-critical": "critical.json",
}


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


def bundle_directory(project_root: Path) -> Path:
    return project_root / ".research" / "bundles"


def bundle_path(
    project_root: Path,
    command: str,
    path_value: str | None,
) -> Path | None:
    if path_value == "-":
        return None
    if path_value is None:
        return bundle_directory(project_root) / BUNDLE_DEFAULTS[command]

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _load_json_object(
    project_root: Path,
    command: str,
    path_value: str | None,
) -> dict[str, Any]:
    path = bundle_path(project_root, command, path_value)
    if path is None:
        raw = json.load(sys.stdin)
    else:
        if not path.is_file():
            raise ResearchDbError(f"bundle 文件不存在：{path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ResearchDbError("bundle 输入必须是 JSON object。")
    return raw


def cmd_record_search(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        record_search_run(
            project_root,
            _load_json_object(project_root, "record-search", args.bundle),
        )
    )
    return 0


def cmd_search_runs(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(list_search_runs(project_root, limit=args.limit))
    return 0


def cmd_candidates(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        list_candidates(
            project_root,
            relevance_status=args.relevance,
            acquisition_status=args.acquisition,
            reading_priority=args.priority,
            limit=args.limit,
        )
    )
    return 0


def cmd_update_candidate(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        update_candidate(
            project_root,
            args.candidate_id,
            _load_json_object(project_root, "update-candidate", args.bundle),
        )
    )
    return 0


def cmd_ingest_paper(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    bundle: PaperIngestBundle = _load_json_object(
        project_root, "ingest-paper", args.bundle
    )
    emit(ingest_paper(project_root, bundle))
    return 0


def cmd_ingest_reading(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        ingest_reading(
            project_root,
            _load_json_object(project_root, "ingest-reading", args.bundle),
        )
    )
    return 0


def cmd_ingest_critical(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        ingest_critical(
            project_root,
            _load_json_object(project_root, "ingest-critical", args.bundle),
        )
    )
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(evidence_packet(project_root, args.query, limit=args.limit))
    return 0


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

    record_search_parser = subparsers.add_parser(
        "record-search",
        help="原子记录一次文献检索及本次发现的 candidate。",
    )
    record_search_parser.add_argument(
        "bundle",
        nargs="?",
        help="Search Run JSON bundle；默认 .research/bundles/search.json；传 '-' 从 stdin 读取。",
    )
    record_search_parser.set_defaults(handler=cmd_record_search)

    search_runs_parser = subparsers.add_parser(
        "search-runs", help="列出已记录的文献检索运行。"
    )
    search_runs_parser.add_argument("--limit", type=int, default=50)
    search_runs_parser.set_defaults(handler=cmd_search_runs)

    candidates_parser = subparsers.add_parser(
        "candidates", help="列出并过滤文献发现 candidate 队列。"
    )
    candidates_parser.add_argument("--relevance")
    candidates_parser.add_argument("--acquisition")
    candidates_parser.add_argument("--priority")
    candidates_parser.add_argument("--limit", type=int, default=50)
    candidates_parser.set_defaults(handler=cmd_candidates)

    update_candidate_parser = subparsers.add_parser(
        "update-candidate", help="更新 candidate 的 identity/relevance/acquisition/priority 状态。"
    )
    update_candidate_parser.add_argument("candidate_id", type=int)
    update_candidate_parser.add_argument(
        "bundle",
        nargs="?",
        help="Candidate update JSON；默认 .research/bundles/candidate-update.json；传 '-' 从 stdin 读取。",
    )
    update_candidate_parser.set_defaults(handler=cmd_update_candidate)

    evidence_parser = subparsers.add_parser(
        "evidence",
        help="返回与问题相关的证据单元和关系图，不进行科研强度判断。",
    )
    evidence_parser.add_argument("query", help="科研问题或关键词。")
    evidence_parser.add_argument("--limit", type=int, default=20)
    evidence_parser.set_defaults(handler=cmd_evidence)

    bundle_commands = [
        (
            "ingest-paper",
            "登记一篇已获取论文及其 artifact provenance。",
            "Paper acquisition JSON bundle；默认 .research/bundles/paper.json；传 '-' 从 stdin 读取。",
            cmd_ingest_paper,
        ),
        (
            "ingest-reading",
            "原子写入 Pass 1 Reconstruction 及知识单元。",
            "Reconstruction JSON bundle；默认 .research/bundles/reconstruction.json；传 '-' 从 stdin 读取。",
            cmd_ingest_reading,
        ),
        (
            "ingest-critical",
            "原子写入 Pass 2 Critical Audit，并可关联人类 sidecar。",
            "Critical Audit JSON bundle；默认 .research/bundles/critical.json；传 '-' 从 stdin 读取。",
            cmd_ingest_critical,
        ),
    ]
    for name, help_text, bundle_help, handler in bundle_commands:
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("bundle", nargs="?", help=bundle_help)
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
