from __future__ import annotations

from pathlib import Path
from typing import Any

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError, connect


NODE_KINDS = {
    "objective",
    "question",
    "hypothesis",
    "design",
    "study",
    "analysis",
    "observation",
    "claim",
}
WORKFLOW_STATUSES = {"open", "active", "blocked", "resolved", "closed"}
BRANCH_PRIORITIES = {"primary", "secondary", "parked"}
RELATIONS = {
    "spawned_from",
    "addresses",
    "tests",
    "supports",
    "weakens",
    "contradicts",
    "qualifies",
    "alternative_to",
    "depends_on",
    "uses",
    "produces",
}
EVIDENCE_RELATIONS = {"supports", "weakens", "contradicts", "qualifies"}
_ALLOWED_STATUS_TRANSITIONS = {
    "open": WORKFLOW_STATUSES,
    "active": WORKFLOW_STATUSES,
    "blocked": {"blocked", "open", "active", "closed"},
    "resolved": {"resolved", "closed"},
    "closed": {"closed"},
}


def _node_by_slug(connection: Any, slug: str, *, field: str) -> Any:
    row = connection.execute("SELECT * FROM research_nodes WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ResearchDbError(f"{field} 引用不存在的 Research Node：{slug}")
    return row


def _optional_local_path(project_root: Path, value: object, *, field: str) -> str | None:
    if common.text(value) is None:
        return None
    return common.local_path(project_root, value, field=field, require_file=True)


def record_research_node(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    slug = common.slug(bundle.get("slug"))
    kind = common.enum_value(bundle.get("kind"), NODE_KINDS, default="question", field="node kind")
    label = common.text(bundle.get("label"), required=True, field="node label")
    scientific_scope = common.text(bundle.get("scientific_scope"))
    workflow_status = common.enum_value(
        bundle.get("workflow_status"), WORKFLOW_STATUSES, default="open", field="workflow_status"
    )
    branch_priority = common.enum_value(
        bundle.get("branch_priority"), BRANCH_PRIORITIES, default="secondary", field="branch_priority"
    )
    parent_slug = common.text(bundle.get("parent_slug"))
    canonical_entity_type = common.text(bundle.get("canonical_entity_type"))
    canonical_entity_id = common.text(bundle.get("canonical_entity_id"))
    if (canonical_entity_type is None) != (canonical_entity_id is None):
        raise ResearchDbError("canonical_entity_type 与 canonical_entity_id 必须同时提供或同时省略。")
    artifact_path = _optional_local_path(
        project_root, bundle.get("artifact_path"), field="research node artifact_path"
    )
    now = common.now()

    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            parent_id: int | None = None
            if parent_slug:
                parent = _node_by_slug(connection, parent_slug, field="parent_slug")
                parent_id = int(parent["id"])
                if str(parent["slug"]) == slug:
                    raise ResearchDbError("Research Node 不能把自己设为 parent。")

            existing = connection.execute(
                "SELECT * FROM research_nodes WHERE slug = ?", (slug,)
            ).fetchone()
            closed_at = now if workflow_status == "closed" else None
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO research_nodes(
                        slug, kind, label, scientific_scope, workflow_status, branch_priority,
                        parent_node_id, canonical_entity_type, canonical_entity_id,
                        artifact_path, created_at, updated_at, closed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        kind,
                        label,
                        scientific_scope,
                        workflow_status,
                        branch_priority,
                        parent_id,
                        canonical_entity_type,
                        canonical_entity_id,
                        artifact_path,
                        now,
                        now,
                        closed_at,
                    ),
                )
                node_id = int(cursor.lastrowid)
            else:
                node_id = int(existing["id"])
                immutable = {
                    "kind": kind,
                    "label": label,
                    "scientific_scope": scientific_scope,
                    "parent_node_id": parent_id,
                    "canonical_entity_type": canonical_entity_type,
                    "canonical_entity_id": canonical_entity_id,
                    "artifact_path": artifact_path,
                }
                changed = [
                    field
                    for field, value in immutable.items()
                    if (existing[field] if existing[field] is not None else None) != value
                ]
                if changed:
                    raise ResearchDbError(
                        "Research Node 的科学身份字段不可静默改写："
                        + ", ".join(changed)
                        + "。科学问题或对象实质改变时建立新 Node。"
                    )
                old_status = str(existing["workflow_status"])
                if workflow_status not in _ALLOWED_STATUS_TRANSITIONS[old_status]:
                    raise ResearchDbError(
                        f"Research Node workflow_status 不能从 {old_status} 变为 {workflow_status}。"
                    )
                if old_status == "closed":
                    closed_at = existing["closed_at"]
                elif workflow_status != "closed":
                    closed_at = None
                connection.execute(
                    """
                    UPDATE research_nodes
                    SET workflow_status = ?, branch_priority = ?, updated_at = ?, closed_at = ?
                    WHERE id = ?
                    """,
                    (workflow_status, branch_priority, now, closed_at, node_id),
                )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'research_node_recorded', 'research_node', ?, ?, ?)
                """,
                (
                    now,
                    str(node_id),
                    "Research Tree node entered canonical project state.",
                    f"node={slug}; kind={kind}; status={workflow_status}; priority={branch_priority}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "node_id": node_id,
        "slug": slug,
        "kind": kind,
        "workflow_status": workflow_status,
        "branch_priority": branch_priority,
    }


def record_research_edge(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    source_slug = common.slug(bundle.get("source_slug"), field="source_slug")
    target_slug = common.slug(bundle.get("target_slug"), field="target_slug")
    relation = common.enum_value(bundle.get("relation"), RELATIONS, default="depends_on", field="relation")
    basis_type = common.text(bundle.get("basis_type"))
    basis_ref = common.text(bundle.get("basis_ref"))
    note = common.text(bundle.get("note"))
    if relation in EVIDENCE_RELATIONS and not basis_ref:
        raise ResearchDbError(f"{relation} relation 必须提供 basis_ref。")
    if source_slug == target_slug:
        raise ResearchDbError("Research Edge 不能连接同一个 Node。")
    now = common.now()

    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            source = _node_by_slug(connection, source_slug, field="source_slug")
            target = _node_by_slug(connection, target_slug, field="target_slug")
            existing = connection.execute(
                """
                SELECT id, note FROM research_edges
                WHERE source_node_id = ? AND relation = ? AND target_node_id = ?
                  AND COALESCE(basis_ref, '') = COALESCE(?, '')
                  AND COALESCE(basis_type, '') = COALESCE(?, '')
                """,
                (int(source["id"]), relation, int(target["id"]), basis_ref, basis_type),
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO research_edges(
                        source_node_id, relation, target_node_id, basis_type,
                        basis_ref, note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(source["id"]),
                        relation,
                        int(target["id"]),
                        basis_type,
                        basis_ref,
                        note,
                        now,
                    ),
                )
                edge_id = int(cursor.lastrowid)
            else:
                edge_id = int(existing["id"])
                existing_note = existing["note"] if existing["note"] is not None else None
                if existing_note != note:
                    raise ResearchDbError(
                        "已登记 Research Edge 的 note 不可静默改写；科学关系解释改变时建立新的 relation/basis。"
                    )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'research_edge_recorded', 'research_edge', ?, ?, ?)
                """,
                (
                    now,
                    str(edge_id),
                    "Research Tree semantic relation recorded from main-model judgment.",
                    f"{source_slug} --{relation}--> {target_slug}; basis={basis_ref or 'structural'}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {"ok": True, "edge_id": edge_id, "relation": relation}


def _active_path(connection: Any, active_id: int) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []
    seen: set[int] = set()
    current_id: int | None = active_id
    while current_id is not None:
        if current_id in seen:
            raise ResearchDbError("Research Tree parent chain 出现 cycle。")
        seen.add(current_id)
        row = connection.execute("SELECT * FROM research_nodes WHERE id = ?", (current_id,)).fetchone()
        if row is None:
            raise ResearchDbError("Research Tree state 引用了不存在的 Node。")
        path.append(dict(row))
        current_id = int(row["parent_node_id"]) if row["parent_node_id"] is not None else None
    path.reverse()
    return path


def set_research_tree_state(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    root_slug = common.slug(bundle.get("root_slug"), field="root_slug")
    active_slug = common.slug(bundle.get("active_slug"), field="active_slug")
    now = common.now()

    with connect(common.db_path(project_root)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            root = _node_by_slug(connection, root_slug, field="root_slug")
            active = _node_by_slug(connection, active_slug, field="active_slug")
            path = _active_path(connection, int(active["id"]))
            if not path or int(path[0]["id"]) != int(root["id"]):
                raise ResearchDbError("active_slug 必须位于 root_slug 的结构子树中。")
            connection.execute(
                """
                INSERT INTO research_tree_state(id, root_node_id, active_node_id, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    root_node_id = excluded.root_node_id,
                    active_node_id = excluded.active_node_id,
                    updated_at = excluded.updated_at
                """,
                (int(root["id"]), int(active["id"]), now),
            )
            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'research_tree_state_set', 'research_tree', '1', ?, ?)
                """,
                (
                    now,
                    "Primary active research path updated.",
                    f"root={root_slug}; active={active_slug}; path={'/'.join(str(x['slug']) for x in path)}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {"ok": True, "root_slug": root_slug, "active_slug": active_slug}


def get_research_tree(project_root: Path, *, limit: int = 500) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        nodes = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM research_nodes ORDER BY id LIMIT ?", (limit,)
            )
        ]
        edges = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.*, s.slug AS source_slug, t.slug AS target_slug
                FROM research_edges e
                JOIN research_nodes s ON s.id = e.source_node_id
                JOIN research_nodes t ON t.id = e.target_node_id
                ORDER BY e.id LIMIT ?
                """,
                (limit,),
            )
        ]
        state_row = connection.execute(
            """
            SELECT st.*, r.slug AS root_slug, a.slug AS active_slug
            FROM research_tree_state st
            JOIN research_nodes r ON r.id = st.root_node_id
            JOIN research_nodes a ON a.id = st.active_node_id
            WHERE st.id = 1
            """
        ).fetchone()
        state = dict(state_row) if state_row is not None else None
        active_path = (
            _active_path(connection, int(state_row["active_node_id"]))
            if state_row is not None
            else []
        )
        open_branches = [
            dict(row)
            for row in connection.execute(
                """
                SELECT * FROM research_nodes
                WHERE workflow_status IN ('open', 'active', 'blocked')
                ORDER BY
                    CASE branch_priority WHEN 'primary' THEN 0 WHEN 'secondary' THEN 1 ELSE 2 END,
                    id
                LIMIT ?
                """,
                (limit,),
            )
        ]
    return {
        "ok": True,
        "state": state,
        "active_path": active_path,
        "nodes": nodes,
        "edges": edges,
        "open_branches": open_branches,
    }
