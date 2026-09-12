from __future__ import annotations

from typing import Any, Callable

from research_db_core import discover_project_root
from research_db_ops.downstream import list_analysis_attempts, record_analysis_attempt
from research_db_ops.user_reading import sync_user_reading, user_reading_status


def register_execution_commands(
    subparsers: Any,
    *,
    emit: Callable[[dict[str, Any]], None],
    load_json: Callable[[Any, str, str | None], dict[str, Any]],
) -> None:
    def cmd_record_analysis_attempt(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            record_analysis_attempt(
                project_root,
                load_json(project_root, "record-analysis-attempt", args.bundle),
            )
        )
        return 0

    def cmd_analysis_attempts(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            list_analysis_attempts(
                project_root,
                analysis_slug=args.analysis,
                limit=args.limit,
            )
        )
        return 0

    def cmd_sync_user_reading(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(sync_user_reading(project_root, paper_id=args.paper))
        return 0

    def cmd_user_reading_status(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(user_reading_status(project_root, paper_id=args.paper))
        return 0

    attempts_parser = subparsers.add_parser(
        "analysis-attempts",
        help="列出 Analysis 下由 Git commit 固定的独立执行尝试。",
    )
    attempts_parser.add_argument("--analysis", help="只返回指定 Analysis slug 的 Attempt。")
    attempts_parser.add_argument("--limit", type=int, default=100)
    attempts_parser.set_defaults(handler=cmd_analysis_attempts)

    record_attempt_parser = subparsers.add_parser(
        "record-analysis-attempt",
        help="登记 Analysis 下独立、由 Git commit 固定的执行 Attempt。",
    )
    record_attempt_parser.add_argument(
        "bundle",
        nargs="?",
        help="Analysis Attempt JSON bundle；默认 .research/bundles/analysis-attempt.json；传 '-' 从 stdin 读取。",
    )
    record_attempt_parser.set_defaults(handler=cmd_record_analysis_attempt)

    sync_reading_parser = subparsers.add_parser(
        "sync-user-reading",
        help="同步人类阅读 Markdown 顶部/底部复选框到用户阅读确认 provenance。",
    )
    sync_reading_parser.add_argument("--paper", help="只同步指定 Paper ID。")
    sync_reading_parser.set_defaults(handler=cmd_sync_user_reading)

    reading_status_parser = subparsers.add_parser(
        "user-reading-status",
        help="查看用户是否已确认当前版本的人类阅读 Markdown。",
    )
    reading_status_parser.add_argument("--paper", help="只查看指定 Paper ID。")
    reading_status_parser.set_defaults(handler=cmd_user_reading_status)
