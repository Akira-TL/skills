from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path


def _git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _commit_exists(project_root: Path, ref: str) -> bool:
    return _git(project_root, "rev-parse", "--verify", f"{ref}^{{commit}}").returncode == 0


def _is_ancestor(project_root: Path, ancestor: str, descendant: str) -> bool:
    return _git(project_root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def _changed_paths(project_root: Path, start: str, end: str) -> set[str]:
    result = _git(project_root, "diff", "--name-only", f"{start}..{end}")
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _only_provenance_changes(project_root: Path, start: str, end: str) -> bool:
    if start == end:
        return True
    if not _is_ancestor(project_root, start, end):
        return False
    return _changed_paths(project_root, start, end) <= {".research/research.sqlite"}


def _is_annotated_tag(project_root: Path, tag: str) -> bool:
    result = _git(project_root, "cat-file", "-t", f"refs/tags/{tag}")
    return result.returncode == 0 and result.stdout.strip() == "tag"


def _merge_parents(project_root: Path, commit: str) -> list[str]:
    result = _git(project_root, "rev-list", "--parents", "-n", "1", commit)
    if result.returncode != 0:
        return []
    return result.stdout.split()[1:]


def _is_merge_commit(project_root: Path, commit: str) -> bool:
    return len(_merge_parents(project_root, commit)) >= 2


def research_tree_completion_readiness(project_root: Path) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "checked": True,
            "blockers": [{"reason": "database_missing"}],
            "node_count": 0,
            "edge_count": 0,
            "state_present": False,
        }

    blockers: list[dict[str, Any]] = []
    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {"research_nodes", "research_edges", "research_tree_state", "research_git_branches"}
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": False,
                "checked": True,
                "blockers": [{"reason": "research_tree_schema_missing", "tables": missing}],
                "node_count": 0,
                "edge_count": 0,
                "state_present": False,
            }

        node_count = int(connection.execute("SELECT COUNT(*) FROM research_nodes").fetchone()[0])
        edge_count = int(connection.execute("SELECT COUNT(*) FROM research_edges").fetchone()[0])
        state = connection.execute(
            """
            SELECT st.root_node_id, st.active_node_id,
                   r.slug AS root_slug, r.parent_node_id AS root_parent_id,
                   a.slug AS active_slug, a.workflow_status AS active_status
            FROM research_tree_state st
            LEFT JOIN research_nodes r ON r.id = st.root_node_id
            LEFT JOIN research_nodes a ON a.id = st.active_node_id
            WHERE st.id = 1
            """
        ).fetchone()
        state_present = state is not None

        if node_count == 0:
            if state_present:
                blockers.append({"reason": "research_tree_state_without_nodes"})
        elif not state_present:
            blockers.append({"reason": "research_tree_state_missing"})
        else:
            if state["root_slug"] is None or state["active_slug"] is None:
                blockers.append({"reason": "research_tree_state_dangling"})
            else:
                if state["root_parent_id"] is not None:
                    blockers.append(
                        {
                            "reason": "research_tree_root_has_parent",
                            "root": state["root_slug"],
                        }
                    )
                seen: set[int] = set()
                current_id: int | None = int(state["active_node_id"])
                reached_root = False
                while current_id is not None:
                    if current_id in seen:
                        blockers.append({"reason": "research_tree_parent_cycle"})
                        break
                    seen.add(current_id)
                    row = connection.execute(
                        "SELECT id, parent_node_id FROM research_nodes WHERE id = ?",
                        (current_id,),
                    ).fetchone()
                    if row is None:
                        blockers.append({"reason": "research_tree_parent_chain_dangling"})
                        break
                    if int(row["id"]) == int(state["root_node_id"]):
                        reached_root = True
                        break
                    current_id = (
                        int(row["parent_node_id"])
                        if row["parent_node_id"] is not None
                        else None
                    )
                if not reached_root:
                    blockers.append(
                        {
                            "reason": "research_tree_active_outside_root",
                            "root": state["root_slug"],
                            "active": state["active_slug"],
                        }
                    )

        workflow_started = connection.execute(
            "SELECT value FROM meta WHERE key = 'research_git_workflow_started_at'"
        ).fetchone()
        if workflow_started is not None:
            for node in connection.execute(
                """
                SELECT slug, kind, workflow_status, closure_reason, updated_at
                FROM research_nodes
                WHERE workflow_status = 'closed' AND updated_at >= ?
                ORDER BY id
                """,
                (str(workflow_started["value"]),),
            ):
                if not node["closure_reason"] or not str(node["closure_reason"]).strip():
                    blockers.append(
                        {
                            "reason": "research_tree_closed_without_reason",
                            "node": node["slug"],
                        }
                    )

        for branch in connection.execute(
            """
            SELECT b.*, n.slug AS node_slug, n.kind AS node_kind
            FROM research_git_branches b
            JOIN research_nodes n ON n.id = b.node_id
            ORDER BY b.id
            """
        ):
            expected = f"research/{branch['node_kind']}/{branch['node_slug']}"
            if str(branch["branch_name"]) != expected:
                blockers.append(
                    {
                        "reason": "research_git_branch_name_invalid",
                        "node": branch["node_slug"],
                        "branch": branch["branch_name"],
                        "expected": expected,
                    }
                )
            base_commit = str(branch["base_commit"])
            tip_commit = str(branch["tip_commit"])
            if not _commit_exists(project_root, base_commit) or not _commit_exists(project_root, tip_commit):
                blockers.append(
                    {
                        "reason": "research_git_commit_missing",
                        "node": branch["node_slug"],
                        "base_commit": base_commit,
                        "tip_commit": tip_commit,
                    }
                )
                continue
            if not _is_ancestor(project_root, base_commit, tip_commit):
                blockers.append(
                    {
                        "reason": "research_git_base_not_ancestor",
                        "node": branch["node_slug"],
                    }
                )
            disposition = str(branch["disposition"])
            if disposition == "active":
                ref = f"refs/heads/{branch['branch_name']}"
                current = _git(project_root, "rev-parse", "--verify", ref)
                current_commit = current.stdout.strip() if current.returncode == 0 else ""
                if not current_commit or not _only_provenance_changes(project_root, tip_commit, current_commit):
                    blockers.append(
                        {
                            "reason": "research_git_active_branch_out_of_sync",
                            "node": branch["node_slug"],
                            "branch": branch["branch_name"],
                        }
                    )
            elif disposition == "merged":
                final_ref = str(branch["final_ref"] or "")
                merge_parents = _merge_parents(project_root, final_ref) if final_ref else []
                if (
                    not final_ref
                    or not _commit_exists(project_root, final_ref)
                    or len(merge_parents) < 2
                    or merge_parents[0] != base_commit
                    or not _is_ancestor(project_root, tip_commit, final_ref)
                    or not _is_ancestor(project_root, final_ref, "main")
                ):
                    blockers.append(
                        {
                            "reason": "research_git_merged_tip_not_in_main",
                            "node": branch["node_slug"],
                            "final_ref": final_ref,
                        }
                    )
            elif disposition == "archived":
                expected_tag = f"research-closed/{branch['node_kind']}/{branch['node_slug']}"
                if str(branch["final_ref"]) != expected_tag:
                    blockers.append(
                        {
                            "reason": "research_git_archive_ref_invalid",
                            "node": branch["node_slug"],
                            "expected": expected_tag,
                        }
                    )
                tag_commit = _git(project_root, "rev-parse", "--verify", f"{expected_tag}^{{commit}}")
                archived_commit = tag_commit.stdout.strip() if tag_commit.returncode == 0 else ""
                if (
                    not archived_commit
                    or not _is_annotated_tag(project_root, expected_tag)
                    or not _only_provenance_changes(project_root, tip_commit, archived_commit)
                ):
                    blockers.append(
                        {
                            "reason": "research_git_archive_tag_mismatch",
                            "node": branch["node_slug"],
                            "tag": expected_tag,
                        }
                    )

    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "node_count": node_count,
        "edge_count": edge_count,
        "state_present": state_present,
    }
