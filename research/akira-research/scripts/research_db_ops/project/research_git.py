from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError, connect


BRANCHABLE_KINDS = {"question", "design", "study", "analysis"}
DISPOSITIONS = {"active", "merged", "archived"}


def _git(project_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(project_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise ResearchDbError(f"Git 命令失败：git {' '.join(args)}：{detail}")
    return result


def _commit(project_root: Path, ref: str, *, field: str) -> str:
    result = _git(project_root, "rev-parse", "--verify", f"{ref}^{{commit}}", check=False)
    if result.returncode != 0:
        raise ResearchDbError(f"{field} 不是可解析的 Git commit/ref：{ref}")
    return result.stdout.strip()


def _branch_exists(project_root: Path, branch: str) -> bool:
    return (
        _git(project_root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode
        == 0
    )


def _tag_exists(project_root: Path, tag: str) -> bool:
    return _git(project_root, "show-ref", "--verify", "--quiet", f"refs/tags/{tag}", check=False).returncode == 0


def _is_ancestor(project_root: Path, ancestor: str, descendant: str) -> bool:
    return _git(project_root, "merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode == 0


def _changed_paths(project_root: Path, start: str, end: str) -> set[str]:
    result = _git(project_root, "diff", "--name-only", f"{start}..{end}", check=False)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _merge_parents(project_root: Path, commit: str) -> list[str]:
    result = _git(project_root, "rev-list", "--parents", "-n", "1", commit, check=False)
    if result.returncode != 0:
        return []
    parts = result.stdout.split()
    return parts[1:]


def _is_merge_commit(project_root: Path, commit: str) -> bool:
    return len(_merge_parents(project_root, commit)) >= 2


def _material_tip(project_root: Path, previous_tip: str, branch_head: str) -> str:
    if previous_tip == branch_head:
        return previous_tip
    if not _is_ancestor(project_root, previous_tip, branch_head):
        raise ResearchDbError(
            "科研 branch 已登记的 tip 不再是当前 tip 的祖先；"
            "不要对已进入科研 provenance 的 branch 执行 rebase/reset/amend 历史重写。"
        )
    changed = _changed_paths(project_root, previous_tip, branch_head)
    if changed and changed <= {".research/research.sqlite"}:
        return previous_tip
    return branch_head


def record_research_branch(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    node_slug = common.slug(bundle.get("node_slug"), field="node_slug")
    disposition = common.enum_value(
        bundle.get("disposition"), DISPOSITIONS, default="active", field="disposition"
    )
    closure_reason = common.text(bundle.get("closure_reason"))

    with connect(common.db_path(project_root)) as connection:
        node = connection.execute(
            "SELECT id, slug, kind FROM research_nodes WHERE slug = ?", (node_slug,)
        ).fetchone()
        if node is None:
            raise ResearchDbError(f"node_slug 引用不存在的 Research Node：{node_slug}")
        kind = str(node["kind"])
        if kind not in BRANCHABLE_KINDS:
            raise ResearchDbError(
                "只有 question/design/study/analysis Research Node 才建立科研 Git branch；"
                f"当前 kind={kind}。"
            )
        branch_name = f"research/{kind}/{node_slug}"
        archive_tag = f"research-closed/{kind}/{node_slug}"

        if not _branch_exists(project_root, branch_name):
            raise ResearchDbError(
                f"科研分支不存在：{branch_name}。先从真实分叉点创建该 branch，再登记 provenance。"
            )
        branch_head = _commit(project_root, branch_name, field="research branch")
        if _git(project_root, "show-ref", "--verify", "--quiet", "refs/heads/main", check=False).returncode != 0:
            raise ResearchDbError("科研 Git 工作流要求 canonical branch 为 main。")
        existing = connection.execute(
            "SELECT * FROM research_git_branches WHERE node_id = ?", (int(node["id"]),)
        ).fetchone()
        if existing is None:
            if disposition != "active":
                raise ResearchDbError(
                    "Research branch 必须在仍为 active 时首次登记，以固定真实分叉点；"
                    "不能等 merge/archive 后再事后推断 base commit。"
                )
            base = _git(project_root, "merge-base", "main", branch_name, check=False)
            if base.returncode != 0 or not base.stdout.strip():
                raise ResearchDbError(f"无法确定 main 与 {branch_name} 的分叉点。")
            base_commit = base.stdout.strip()
        else:
            base_commit = str(existing["base_commit"])

        tip_commit = (
            branch_head
            if existing is None
            else _material_tip(project_root, str(existing["tip_commit"]), branch_head)
        )

        final_ref: str | None = None
        if disposition == "active":
            if closure_reason:
                raise ResearchDbError("active research branch 不应填写 closure_reason。")
        elif disposition == "merged":
            if not closure_reason:
                raise ResearchDbError("merged research branch 必须记录接受/关闭原因。")
            main_commit = _commit(project_root, "main", field="main")
            if not _is_ancestor(project_root, tip_commit, main_commit):
                raise ResearchDbError(
                    f"{branch_name} 的 tip 尚未进入 main；科研路线接受时必须先使用保留拓扑的 merge。"
                )
            parents = _merge_parents(project_root, main_commit)
            if len(parents) < 2:
                raise ResearchDbError(
                    "接受科研路线时 main 当前 HEAD 必须是保留拓扑的 merge commit；"
                    "不要 squash 或 fast-forward 后再事后登记。"
                )
            if parents[0] != base_commit:
                raise ResearchDbError(
                    "科研 branch 打开后 main 已经推进；旧分支不能直接并入新的 canonical state。"
                    "请归档旧路线，或从当前 main 建立新 branch 继承仍然有效的工作。"
                )
            final_ref = main_commit
        else:
            if not closure_reason:
                raise ResearchDbError("archived research branch 必须记录关闭原因。")
            if _tag_exists(project_root, archive_tag):
                raise ResearchDbError(
                    f"archival tag 已存在：{archive_tag}。先完成 closure provenance 再建立 tag，"
                    "不要移动或复用既有归档 tag。"
                )
            final_ref = archive_tag

        now = common.now()
        connection.execute("BEGIN IMMEDIATE")
        try:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO research_git_branches(
                        node_id, branch_name, base_commit, tip_commit, disposition,
                        final_ref, closure_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(node["id"]), branch_name, base_commit, tip_commit, disposition,
                        final_ref, closure_reason, now, now,
                    ),
                )
            else:
                if str(existing["branch_name"]) != branch_name:
                    raise ResearchDbError("Research Node 已绑定其他 Git branch；branch identity 不可静默改写。")
                old_disposition = str(existing["disposition"])
                if old_disposition != "active" and disposition != old_disposition:
                    raise ResearchDbError("已 merged/archived 的科研 branch provenance 不可重新激活或改写。")
                connection.execute(
                    """
                    UPDATE research_git_branches
                    SET tip_commit = ?, disposition = ?, final_ref = ?, closure_reason = ?, updated_at = ?
                    WHERE node_id = ?
                    """,
                    (tip_commit, disposition, final_ref, closure_reason, now, int(node["id"])),
                )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'research_git_branch_recorded', 'research_node', ?, ?, ?)
                """,
                (
                    now,
                    str(node["id"]),
                    closure_reason or "Research branch provenance synchronized.",
                    f"branch={branch_name}; disposition={disposition}; tip={tip_commit}; final_ref={final_ref or ''}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "node_slug": node_slug,
        "kind": kind,
        "branch_name": branch_name,
        "base_commit": base_commit,
        "tip_commit": tip_commit,
        "disposition": disposition,
        "final_ref": final_ref,
    }


def list_research_branches(project_root: Path, *, limit: int = 100) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT b.*, n.slug AS node_slug, n.kind AS node_kind, n.workflow_status
                FROM research_git_branches b
                JOIN research_nodes n ON n.id = b.node_id
                ORDER BY b.id LIMIT ?
                """,
                (limit,),
            )
        ]
    return {"ok": True, "branches": rows}
