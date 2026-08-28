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
from research_db_ops.acquisition import list_acquisition_attempts, record_acquisition_attempt
from research_db_ops.candidates import (
    discovery_readiness,
    list_candidates,
    merge_candidates,
    update_candidate,
)
from research_db_ops.completion import validate_completion
from research_db_ops.discovery import list_search_runs, record_search_run
from research_db_ops.downstream import (
    list_analyses,
    list_datasets,
    record_analysis,
    record_dataset,
)
from research_db_ingest import PaperIngestBundle, ingest_paper
from research_db_ops.query import (
    evidence_packet,
    get_paper,
    list_entities,
    paper_history,
    related_papers,
    search_knowledge,
)
from research_db_reading import ingest_reading
from research_db_ops.relations import add_relation


BUNDLE_DEFAULTS = {
    "record-search": "search.json",
    "record-access-attempt": "access-attempt.json",
    "update-candidate": "candidate-update.json",
    "relate": "relation.json",
    "ingest-paper": "paper.json",
    "ingest-reading": "reconstruction.json",
    "ingest-critical": "critical.json",
    "record-dataset": "dataset.json",
    "record-analysis": "analysis.json",
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
    payload = validate_completion(project_root) if getattr(args, "completion", False) else validate(project_root)
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


def cmd_record_access_attempt(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        record_acquisition_attempt(
            project_root,
            _load_json_object(project_root, "record-access-attempt", args.bundle),
        )
    )
    return 0


def cmd_access_attempts(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        list_acquisition_attempts(
            project_root,
            candidate_id=args.candidate,
            paper_id=args.paper,
            target_kind=args.target_kind,
            limit=args.limit,
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


def cmd_merge_candidates(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        merge_candidates(
            project_root,
            args.keep_id,
            args.merge_id,
            reason=args.reason,
        )
    )
    return 0


def cmd_discovery_status(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    payload = discovery_readiness(project_root)
    emit(payload)
    return 0 if payload["ready_for_saturation"] else 1


def cmd_relate(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        add_relation(
            project_root,
            _load_json_object(project_root, "relate", args.bundle),
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


def cmd_search(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        search_knowledge(
            project_root,
            args.query,
            entity_types=args.entity_type,
            paper_id=args.paper,
            limit=args.limit,
        )
    )
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(get_paper(project_root, args.paper_id))
    return 0


def _cmd_entity_list(args: argparse.Namespace, entity_type: str) -> int:
    project_root = discover_project_root(args.project)
    emit(
        list_entities(
            project_root,
            entity_type,
            query=args.query,
            paper_id=args.paper,
            limit=args.limit,
            severity=getattr(args, "severity", None),
            nature=getattr(args, "nature", None),
        )
    )
    return 0


def cmd_methods(args: argparse.Namespace) -> int:
    return _cmd_entity_list(args, "method")


def cmd_claims(args: argparse.Namespace) -> int:
    return _cmd_entity_list(args, "claim")


def cmd_issues(args: argparse.Namespace) -> int:
    return _cmd_entity_list(args, "issue")


def cmd_related(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(related_papers(project_root, args.paper_id))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(paper_history(project_root, args.paper_id, limit=args.limit))
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(evidence_packet(project_root, args.query, limit=args.limit))
    return 0


def cmd_record_dataset(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        record_dataset(
            project_root,
            _load_json_object(project_root, "record-dataset", args.bundle),
        )
    )
    return 0


def cmd_record_analysis(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(
        record_analysis(
            project_root,
            _load_json_object(project_root, "record-analysis", args.bundle),
        )
    )
    return 0


def cmd_datasets(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(list_datasets(project_root, limit=args.limit))
    return 0


def cmd_analyses(args: argparse.Namespace) -> int:
    project_root = discover_project_root(args.project)
    emit(list_analyses(project_root, limit=args.limit))
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
        if name == "validate":
            command_parser.add_argument(
                "--completion",
                action="store_true",
                help="额外检查 Discovery 队列闭合与科研项目 Git provenance 完成门禁。",
            )
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

    access_attempt_parser = subparsers.add_parser(
        "record-access-attempt",
        help="记录一次正文/附件/代码数据获取尝试及其真实结果。",
    )
    access_attempt_parser.add_argument(
        "bundle",
        nargs="?",
        help="Access Attempt JSON；默认 .research/bundles/access-attempt.json；传 '-' 从 stdin 读取。",
    )
    access_attempt_parser.set_defaults(handler=cmd_record_access_attempt)

    access_attempts_parser = subparsers.add_parser(
        "access-attempts", help="列出已记录的 acquisition attempts。"
    )
    access_attempts_parser.add_argument("--candidate", type=int)
    access_attempts_parser.add_argument("--paper")
    access_attempts_parser.add_argument("--target-kind")
    access_attempts_parser.add_argument("--limit", type=int, default=100)
    access_attempts_parser.set_defaults(handler=cmd_access_attempts)

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

    merge_candidates_parser = subparsers.add_parser(
        "merge-candidates",
        help="合并已确认属于同一 scholarly work 的 Candidate，并保留全部 Search Run provenance。",
    )
    merge_candidates_parser.add_argument("keep_id", type=int)
    merge_candidates_parser.add_argument("merge_id", type=int)
    merge_candidates_parser.add_argument(
        "--reason", required=True, help="为什么确认两条 Candidate 属于同一 scholarly work。"
    )
    merge_candidates_parser.set_defaults(handler=cmd_merge_candidates)

    discovery_status_parser = subparsers.add_parser(
        "discovery-status",
        help="检查 Candidate 队列是否足以支持声称 practical conceptual saturation。",
    )
    discovery_status_parser.set_defaults(handler=cmd_discovery_status)

    search_parser = subparsers.add_parser(
        "search", help="FTS 检索已沉淀的 Paper/Method/Experiment/Observation/Claim/Issue/Lead。"
    )
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--entity-type",
        action="append",
        choices=["paper", "method", "experiment", "observation", "claim", "issue", "lead"],
    )
    search_parser.add_argument("--paper")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.set_defaults(handler=cmd_search)

    paper_parser = subparsers.add_parser("paper", help="读取一篇 Paper 的身份、artifact、阅读运行与知识计数。")
    paper_parser.add_argument("paper_id")
    paper_parser.set_defaults(handler=cmd_paper)

    for name, help_text, handler in (
        ("methods", "查询或列出 Method。", cmd_methods),
        ("claims", "查询或列出 Claim。", cmd_claims),
        ("issues", "查询或列出 Critical Issue。", cmd_issues),
    ):
        entity_parser = subparsers.add_parser(name, help=help_text)
        entity_parser.add_argument("query", nargs="?")
        entity_parser.add_argument("--paper")
        entity_parser.add_argument("--limit", type=int, default=50)
        if name == "issues":
            entity_parser.add_argument("--severity")
            entity_parser.add_argument("--nature")
        entity_parser.set_defaults(handler=handler)

    related_parser = subparsers.add_parser("related", help="返回通过关系图连接的其他 Paper。")
    related_parser.add_argument("paper_id")
    related_parser.set_defaults(handler=cmd_related)

    history_parser = subparsers.add_parser("history", help="返回一篇 Paper 的语义 change log。")
    history_parser.add_argument("paper_id")
    history_parser.add_argument("--limit", type=int, default=100)
    history_parser.set_defaults(handler=cmd_history)

    relate_parser = subparsers.add_parser(
        "relate",
        help="写入主模型已核验的跨实体/跨论文 relation；脚本不自动推断科研关系。",
    )
    relate_parser.add_argument(
        "bundle",
        nargs="?",
        help="Relation JSON；默认 .research/bundles/relation.json；传 '-' 从 stdin 读取。",
    )
    relate_parser.set_defaults(handler=cmd_relate)

    evidence_parser = subparsers.add_parser(
        "evidence",
        help="返回与问题相关的证据单元和关系图，不进行科研强度判断。",
    )
    evidence_parser.add_argument("query", help="科研问题或关键词。")
    evidence_parser.add_argument("--limit", type=int, default=20)
    evidence_parser.set_defaults(handler=cmd_evidence)

    for name, help_text, handler in (
        ("datasets", "列出项目级 Dataset provenance。", cmd_datasets),
        ("analyses", "列出项目级 Analysis Run、artifact、修订与项目 Observation。", cmd_analyses),
    ):
        downstream_parser = subparsers.add_parser(name, help=help_text)
        downstream_parser.add_argument("--limit", type=int, default=100)
        downstream_parser.set_defaults(handler=handler)

    bundle_commands = [
        (
            "record-dataset",
            "登记项目自身数据集的身份、推断单位和 artifact provenance。",
            "Dataset JSON bundle；默认 .research/bundles/dataset.json；传 '-' 从 stdin 读取。",
            cmd_record_dataset,
        ),
        (
            "record-analysis",
            "登记或推进 Analysis Run，并持久化结果 artifact、修订与项目 Observation。",
            "Analysis JSON bundle；默认 .research/bundles/analysis.json；传 '-' 从 stdin 读取。",
            cmd_record_analysis,
        ),
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
