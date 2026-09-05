from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path


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
        required = {"research_nodes", "research_edges", "research_tree_state"}
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

    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "node_count": node_count,
        "edge_count": edge_count,
        "state_present": state_present,
    }
