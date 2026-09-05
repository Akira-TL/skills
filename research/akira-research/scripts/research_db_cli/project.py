from __future__ import annotations

from typing import Any, Callable

from research_db_core import discover_project_root
from research_db_ops.project import (
    get_research_tree,
    list_studies,
    record_research_edge,
    record_research_node,
    record_study,
    set_research_tree_state,
)


PROJECT_BUNDLE_DEFAULTS = {
    "record-research-node": "research-node.json",
    "record-research-edge": "research-edge.json",
    "set-research-tree-state": "research-tree-state.json",
    "record-study": "study.json",
}


def register_project_commands(
    subparsers: Any,
    *,
    emit: Callable[[dict[str, Any]], None],
    load_json: Callable[[Any, str, str | None], dict[str, Any]],
) -> None:
    def cmd_record_research_node(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            record_research_node(
                project_root,
                load_json(project_root, "record-research-node", args.bundle),
            )
        )
        return 0

    def cmd_record_research_edge(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            record_research_edge(
                project_root,
                load_json(project_root, "record-research-edge", args.bundle),
            )
        )
        return 0

    def cmd_set_research_tree_state(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            set_research_tree_state(
                project_root,
                load_json(project_root, "set-research-tree-state", args.bundle),
            )
        )
        return 0

    def cmd_research_tree(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(get_research_tree(project_root, limit=args.limit))
        return 0

    def cmd_record_study(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(
            record_study(
                project_root,
                load_json(project_root, "record-study", args.bundle),
            )
        )
        return 0

    def cmd_studies(args: Any) -> int:
        project_root = discover_project_root(args.project)
        emit(list_studies(project_root, limit=args.limit))
        return 0

    for name, help_text, handler in (
        ("research-tree", "读取项目 Research Tree、active path 与科学关系。", cmd_research_tree),
        ("studies", "列出项目级 Study execution、Sample、Assay 与 deviation provenance。", cmd_studies),
    ):
        parser = subparsers.add_parser(name, help=help_text)
        parser.add_argument("--limit", type=int, default=100)
        parser.set_defaults(handler=handler)

    for name, help_text, bundle_help, handler in (
        (
            "record-research-node",
            "登记或更新一个 Research Tree scientific node 的 workflow state。",
            "Research Node JSON bundle；默认 .research/bundles/research-node.json；传 '-' 从 stdin 读取。",
            cmd_record_research_node,
        ),
        (
            "record-research-edge",
            "登记主模型已核验的 Research Tree 科学关系及其 evidence basis。",
            "Research Edge JSON bundle；默认 .research/bundles/research-edge.json；传 '-' 从 stdin 读取。",
            cmd_record_research_edge,
        ),
        (
            "set-research-tree-state",
            "设置 Root 与 primary active Research Node，并校验 active path。",
            "Research Tree State JSON bundle；默认 .research/bundles/research-tree-state.json；传 '-' 从 stdin 读取。",
            cmd_set_research_tree_state,
        ),
        (
            "record-study",
            "登记真实 Study execution、Sample、Assay、deviation 与 artifact provenance。",
            "Study JSON bundle；默认 .research/bundles/study.json；传 '-' 从 stdin 读取。",
            cmd_record_study,
        ),
    ):
        parser = subparsers.add_parser(name, help=help_text)
        parser.add_argument("bundle", nargs="?", help=bundle_help)
        parser.set_defaults(handler=handler)
