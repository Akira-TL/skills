from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError, connect


ATTEMPT_STATUSES = {"planned", "completed", "selected", "abandoned", "invalid"}
_TERMINAL_STATUSES = {"completed", "selected", "abandoned", "invalid"}
_STATUS_TRANSITIONS = {
    "planned": ATTEMPT_STATUSES,
    "completed": {"completed", "selected", "abandoned"},
    "selected": {"selected"},
    "abandoned": {"abandoned"},
    "invalid": {"invalid"},
}
_ANALYSIS_PATH_RE = re.compile(r"(?:^|[./])(?:\.research/)?analysis/([a-z0-9][a-z0-9-]*)/")


def _git(project_root: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def _commit(project_root: Path, value: object) -> str | None:
    raw = common.text(value)
    if raw is None:
        return None
    result = _git(project_root, "rev-parse", "--verify", f"{raw}^{{commit}}")
    if result.returncode != 0:
        raise ResearchDbError(f"git_commit 不是可解析的 Git commit/ref：{raw}")
    return result.stdout.strip()


def _optional_local_path(project_root: Path, value: object, *, field: str) -> str | None:
    if common.text(value) is None:
        return None
    return common.local_path(project_root, value, field=field)


def _path_exists_at_commit(project_root: Path, commit: str, path: str) -> bool:
    return _git(project_root, "cat-file", "-e", f"{commit}:{path}").returncode == 0


def _source_at_commit(project_root: Path, commit: str, path: str) -> str:
    result = _git(project_root, "show", f"{commit}:{path}")
    if result.returncode != 0:
        raise ResearchDbError(
            f"Analysis code_path 在 Attempt git_commit 中不存在：{path} @ {commit}。"
        )
    return result.stdout


def _code_isolation_blockers(source: str, *, analysis_slug: str) -> list[str]:
    blockers: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ResearchDbError(f"Attempt 对应 Python 入口无法解析：{exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if (
                isinstance(owner, ast.Attribute)
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "sys"
                and owner.attr == "path"
                and node.func.attr in {"append", "insert", "extend"}
            ):
                blockers.append("禁止通过 sys.path 动态修改 Python import 路径。")
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("scripts.analyses."):
                blockers.append("Analysis 不得 import 其他 scripts/analyses 下的分析入口。")
            if node.module.startswith("analysis."):
                blockers.append("Analysis 不得从 analysis/ 人类结果目录 import 代码。")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for match in _ANALYSIS_PATH_RE.finditer(node.value.replace("\\", "/")):
                referenced_slug = match.group(1)
                if referenced_slug != analysis_slug:
                    blockers.append(
                        f"Analysis 不得读取兄弟分析工作目录：{referenced_slug}。"
                    )
    return list(dict.fromkeys(blockers))


def _validate_code_contract(project_root: Path, analysis: Any, commit: str) -> None:
    code_path = str(analysis["code_path"])
    if not (
        code_path.startswith("scripts/analyses/")
        or code_path.startswith("src/")
    ):
        raise ResearchDbError(
            "新 Analysis Attempt 的 code_path 必须位于 scripts/analyses/ 或 src/；"
            "不要把科研实现散放在 analysis/、.research/analysis/ 或全局临时脚本中。"
        )
    if code_path.endswith(".py"):
        blockers = _code_isolation_blockers(
            _source_at_commit(project_root, commit, code_path),
            analysis_slug=str(analysis["slug"]),
        )
        if blockers:
            raise ResearchDbError("Analysis code isolation 失败：" + " ".join(blockers))


def _attempt_path_prefix(analysis_slug: str, attempt_key: str) -> str:
    return f".research/analysis/{analysis_slug}/{attempt_key}/"


def record_analysis_attempt(project_root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    analysis_slug = common.slug(bundle.get("analysis_slug"), field="analysis_slug")
    attempt_key = common.text(bundle.get("attempt_key"), required=True, field="attempt_key")
    assert attempt_key is not None
    if not re.fullmatch(r"[A-Z][0-9]{3,}", attempt_key):
        raise ResearchDbError("attempt_key 必须使用 A001、B002 这类大写字母 + 至少三位数字格式。")
    status = common.enum_value(
        bundle.get("status"), ATTEMPT_STATUSES, default="planned", field="attempt status"
    )
    reason = common.text(bundle.get("reason"), required=True, field="attempt reason")
    decision_reason = common.text(bundle.get("decision_reason"))
    if status == "selected" and not decision_reason:
        raise ResearchDbError("selected Attempt 必须说明 decision_reason。")
    git_commit = _commit(project_root, bundle.get("git_commit"))
    if status != "planned" and git_commit is None:
        raise ResearchDbError("已执行/结束的 Attempt 必须记录 git_commit。")
    config_path = _optional_local_path(project_root, bundle.get("config_path"), field="config_path")
    output_path = _optional_local_path(project_root, bundle.get("output_path"), field="output_path")
    now = common.now()
    started_at = common.text(bundle.get("started_at")) or now
    completed_at = common.text(bundle.get("completed_at"))
    if status in _TERMINAL_STATUSES and completed_at is None:
        completed_at = now
    common.parse_timestamp(started_at, field="attempt started_at")
    if completed_at is not None:
        completed_time = common.parse_timestamp(completed_at, field="attempt completed_at")
        if completed_time < common.parse_timestamp(started_at, field="attempt started_at"):
            raise ResearchDbError("Attempt completed_at 不能早于 started_at。")

    with connect(common.db_path(project_root)) as connection:
        analysis = connection.execute(
            "SELECT * FROM analysis_runs WHERE slug = ?", (analysis_slug,)
        ).fetchone()
        if analysis is None:
            raise ResearchDbError(f"Analysis Attempt 引用不存在的 Analysis：{analysis_slug}")
        if git_commit is not None:
            _validate_code_contract(project_root, analysis, git_commit)
            if config_path is not None and not _path_exists_at_commit(project_root, git_commit, config_path):
                raise ResearchDbError(
                    "Attempt config_path 必须已经存在于所记录的 git_commit；"
                    "参数与代码必须由同一个 Git 状态固定。"
                )

        prefix = _attempt_path_prefix(analysis_slug, attempt_key)
        for field, path in (("config_path", config_path), ("output_path", output_path)):
            if path is not None and not path.startswith(prefix):
                raise ResearchDbError(
                    f"{field} 必须位于当前 Attempt 独立目录 {prefix} 下；不能复用其他 Attempt 的工作文件。"
                )

        parent_id: int | None = None
        parent_key = common.text(bundle.get("parent_attempt_key"))
        if parent_key:
            parent = connection.execute(
                "SELECT id FROM analysis_attempts WHERE analysis_id = ? AND attempt_key = ?",
                (int(analysis["id"]), parent_key),
            ).fetchone()
            if parent is None:
                raise ResearchDbError(f"parent_attempt_key 不存在于当前 Analysis：{parent_key}")
            parent_id = int(parent["id"])

        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT * FROM analysis_attempts WHERE analysis_id = ? AND attempt_key = ?",
                (int(analysis["id"]), attempt_key),
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO analysis_attempts(
                        analysis_id, attempt_key, parent_attempt_id, status, git_commit,
                        config_path, output_path, reason, decision_reason,
                        started_at, completed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(analysis["id"]), attempt_key, parent_id, status, git_commit,
                        config_path, output_path, reason, decision_reason,
                        started_at, completed_at, now, now,
                    ),
                )
                attempt_id = int(cursor.lastrowid)
            else:
                attempt_id = int(existing["id"])
                if str(existing["reason"]) != reason:
                    raise ResearchDbError("Attempt reason 属于创建时 provenance，不可静默改写。")
                if (existing["parent_attempt_id"] or None) != parent_id:
                    raise ResearchDbError("Attempt parent provenance 不可静默改写。")
                old_status = str(existing["status"])
                if status not in _STATUS_TRANSITIONS[old_status]:
                    raise ResearchDbError(f"Attempt status 不能从 {old_status} 变为 {status}。")
                if existing["git_commit"] is not None and git_commit not in {None, str(existing["git_commit"])}:
                    raise ResearchDbError("已记录执行 commit 的 Attempt 不得改写 git_commit；建立新 Attempt。")
                if existing["config_path"] is not None and config_path not in {None, str(existing["config_path"])}:
                    raise ResearchDbError("Attempt config_path 不得静默改写；建立新 Attempt。")
                connection.execute(
                    """
                    UPDATE analysis_attempts
                    SET status = ?, git_commit = COALESCE(git_commit, ?),
                        config_path = COALESCE(config_path, ?), output_path = COALESCE(output_path, ?),
                        decision_reason = COALESCE(?, decision_reason),
                        completed_at = COALESCE(?, completed_at), updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        status, git_commit, config_path, output_path, decision_reason,
                        completed_at, now, attempt_id,
                    ),
                )

            connection.execute(
                """
                INSERT INTO change_log(timestamp, action, entity_type, entity_id, reason, summary)
                VALUES (?, 'analysis_attempt_recorded', 'analysis_attempt', ?, ?, ?)
                """,
                (
                    now,
                    str(attempt_id),
                    reason,
                    f"analysis={analysis_slug}; attempt={attempt_key}; status={status}; commit={git_commit or ''}",
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "ok": True,
        "attempt_id": attempt_id,
        "analysis_slug": analysis_slug,
        "attempt_key": attempt_key,
        "status": status,
        "git_commit": git_commit,
    }


def list_analysis_attempts(
    project_root: Path,
    *,
    analysis_slug: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        params: list[Any] = []
        where = ""
        if analysis_slug:
            where = "WHERE a.slug = ?"
            params.append(analysis_slug)
        params.append(limit)
        rows = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT at.*, a.slug AS analysis_slug, p.attempt_key AS parent_attempt_key
                FROM analysis_attempts at
                JOIN analysis_runs a ON a.id = at.analysis_id
                LEFT JOIN analysis_attempts p ON p.id = at.parent_attempt_id
                {where}
                ORDER BY at.id LIMIT ?
                """,
                params,
            )
        ]
    return {"ok": True, "attempts": rows}
