from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import research_db_ops.common as common
from research_db_support.storage import ResearchDbError, connect


CONTROL_LABEL = "我已阅读并确认当前版本"
TOP_START = "<!-- akira:user-read:top -->"
TOP_END = "<!-- /akira:user-read:top -->"
BOTTOM_START = "<!-- akira:user-read:bottom -->"
BOTTOM_END = "<!-- /akira:user-read:bottom -->"
USER_NOTES_START = "<!-- akira:user-notes:start -->"
USER_NOTES_END = "<!-- /akira:user-notes:end -->"
_CONTROL_RE = re.compile(r"^- \[([ xX])\] \*\*我已阅读并确认当前版本\*\*$", re.MULTILINE)


def confirmation_control(position: str, *, checked: bool = False) -> str:
    if position not in {"top", "bottom"}:
        raise ValueError("position must be top or bottom")
    mark = "x" if checked else " "
    return (
        f"<!-- akira:user-read:{position} -->\n"
        f"- [{mark}] **{CONTROL_LABEL}**\n"
        f"<!-- /akira:user-read:{position} -->"
    )


def _block(text: str, start: str, end: str, *, position: str) -> tuple[str, bool]:
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index < 0 or end_index < 0 or end_index <= start_index:
        raise ResearchDbError(f"人类阅读 Markdown 缺少 {position} 用户阅读确认框。")
    content_start = start_index + len(start)
    content = text[content_start:end_index]
    matches = list(_CONTROL_RE.finditer(content.strip()))
    if len(matches) != 1:
        raise ResearchDbError(f"{position} 用户阅读确认区必须且只能包含一个标准复选框。")
    checked = matches[0].group(1).lower() == "x"
    return content, checked


def parse_confirmation_controls(text: str) -> tuple[bool, bool]:
    _, top = _block(text, TOP_START, TOP_END, position="顶部")
    _, bottom = _block(text, BOTTOM_START, BOTTOM_END, position="底部")
    return top, bottom


def _replace_control(text: str, position: str, *, checked: bool) -> str:
    start = TOP_START if position == "top" else BOTTOM_START
    end = TOP_END if position == "top" else BOTTOM_END
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index < 0 or end_index < 0 or end_index <= start_index:
        raise ResearchDbError(f"缺少 {position} 用户阅读确认区。")
    replacement = confirmation_control(position, checked=checked)
    return text[:start_index] + replacement + text[end_index + len(end):]


def user_notes_block() -> str:
    return f"{USER_NOTES_START}\n\n{USER_NOTES_END}"


def _normalize_user_notes(text: str) -> str:
    start_count = text.count(USER_NOTES_START)
    end_count = text.count(USER_NOTES_END)
    if start_count == 0 and end_count == 0:
        return text
    if start_count != 1 or end_count != 1:
        raise ResearchDbError("人类阅读 Markdown 的用户笔记区边界必须成对且只能出现一次。")
    start_index = text.find(USER_NOTES_START)
    end_index = text.find(USER_NOTES_END)
    if end_index <= start_index:
        raise ResearchDbError("人类阅读 Markdown 的用户笔记区边界顺序无效。")
    return (
        text[:start_index]
        + user_notes_block()
        + text[end_index + len(USER_NOTES_END):]
    )


def normalized_confirmation_text(text: str) -> str:
    parse_confirmation_controls(text)
    normalized = _replace_control(text, "top", checked=False)
    normalized = _replace_control(normalized, "bottom", checked=False)
    return _normalize_user_notes(normalized)


def _content_oid(project_root: Path, text: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(project_root), "hash-object", "--stdin"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown git error"
        raise ResearchDbError(f"无法计算 Git 内容对象版本：{detail}")
    return result.stdout.strip()


def _latest_event(connection: Any, paper_id: str) -> Any | None:
    return connection.execute(
        "SELECT * FROM user_reading_events WHERE paper_id = ? ORDER BY id DESC LIMIT 1",
        (paper_id,),
    ).fetchone()


def _event(connection: Any, *, paper_id: str, action: str, path: str, oid: str, now: str) -> int:
    cursor = connection.execute(
        """
        INSERT INTO user_reading_events(paper_id, action, sidecar_path, content_oid, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (paper_id, action, path, oid, now),
    )
    return int(cursor.lastrowid)


def sync_user_reading(project_root: Path, *, paper_id: str | None = None) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        if paper_id:
            rows = connection.execute(
                """
                SELECT id, sidecar_path FROM papers
                WHERE id = ? AND sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''
                """,
                (paper_id,),
            ).fetchall()
            if not rows:
                raise ResearchDbError(f"Paper 不存在或没有人类阅读 Markdown：{paper_id}")
        else:
            rows = connection.execute(
                """
                SELECT id, sidecar_path FROM papers
                WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''
                ORDER BY id
                """
            ).fetchall()

        results: list[dict[str, Any]] = []
        connection.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                current_paper_id = str(row["id"])
                sidecar_path = str(row["sidecar_path"])
                path = Path(sidecar_path)
                if not path.is_absolute():
                    path = project_root / path
                if not path.is_file():
                    results.append(
                        {
                            "paper_id": current_paper_id,
                            "sidecar_path": sidecar_path,
                            "status": "missing_sidecar",
                            "confirmed_current_version": False,
                        }
                    )
                    continue

                text = path.read_text(encoding="utf-8")
                try:
                    top_checked, bottom_checked = parse_confirmation_controls(text)
                except ResearchDbError as exc:
                    results.append(
                        {
                            "paper_id": current_paper_id,
                            "sidecar_path": sidecar_path,
                            "status": "controls_missing_or_invalid",
                            "error": str(exc),
                            "confirmed_current_version": False,
                        }
                    )
                    continue

                oid = _content_oid(project_root, normalized_confirmation_text(text))
                latest = _latest_event(connection, current_paper_id)
                any_checked = top_checked or bottom_checked
                action: str | None = None
                now = common.now()

                stale_confirmed_version = bool(
                    latest is not None
                    and str(latest["action"]) == "confirmed"
                    and str(latest["content_oid"]) != oid
                )
                if stale_confirmed_version:
                    if not (
                        latest is not None
                        and str(latest["action"]) == "invalidated"
                        and str(latest["content_oid"]) == oid
                    ):
                        _event(
                            connection,
                            paper_id=current_paper_id,
                            action="invalidated",
                            path=sidecar_path,
                            oid=oid,
                            now=now,
                        )
                        action = "invalidated"
                    synchronized = _replace_control(text, "top", checked=False)
                    synchronized = _replace_control(synchronized, "bottom", checked=False)
                    if synchronized != text:
                        path.write_text(synchronized, encoding="utf-8")
                    confirmed = False
                elif any_checked:
                    if not (
                        latest is not None
                        and str(latest["action"]) == "confirmed"
                        and str(latest["content_oid"]) == oid
                    ):
                        _event(
                            connection,
                            paper_id=current_paper_id,
                            action="confirmed",
                            path=sidecar_path,
                            oid=oid,
                            now=now,
                        )
                        action = "confirmed"
                    synchronized = _replace_control(text, "top", checked=True)
                    synchronized = _replace_control(synchronized, "bottom", checked=True)
                    if synchronized != text:
                        path.write_text(synchronized, encoding="utf-8")
                    confirmed = True
                else:
                    if (
                        latest is not None
                        and str(latest["action"]) == "confirmed"
                        and str(latest["content_oid"]) == oid
                    ):
                        _event(
                            connection,
                            paper_id=current_paper_id,
                            action="revoked",
                            path=sidecar_path,
                            oid=oid,
                            now=now,
                        )
                        action = "revoked"
                    confirmed = False

                current_latest = _latest_event(connection, current_paper_id)
                confirmed_current = bool(
                    current_latest is not None
                    and str(current_latest["action"]) == "confirmed"
                    and str(current_latest["content_oid"]) == oid
                )
                results.append(
                    {
                        "paper_id": current_paper_id,
                        "sidecar_path": sidecar_path,
                        "content_oid": oid,
                        "checkboxes": {"top": top_checked, "bottom": bottom_checked},
                        "action": action,
                        "confirmed_current_version": confirmed_current and confirmed,
                    }
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {"ok": True, "papers": results}


def user_reading_status(project_root: Path, *, paper_id: str | None = None) -> dict[str, Any]:
    with connect(common.db_path(project_root)) as connection:
        clauses: list[str] = []
        params: list[Any] = []
        if paper_id:
            clauses.append("p.id = ?")
            params.append(paper_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        papers = connection.execute(
            f"SELECT p.id, p.title, p.sidecar_path FROM papers p {where} ORDER BY p.id",
            params,
        ).fetchall()
        results: list[dict[str, Any]] = []
        for paper in papers:
            latest = _latest_event(connection, str(paper["id"]))
            current_oid: str | None = None
            controls_valid = False
            if paper["sidecar_path"]:
                path = Path(str(paper["sidecar_path"]))
                if not path.is_absolute():
                    path = project_root / path
                if path.is_file():
                    text = path.read_text(encoding="utf-8")
                    try:
                        current_oid = _content_oid(project_root, normalized_confirmation_text(text))
                        controls_valid = True
                    except ResearchDbError:
                        pass
            confirmed_current = bool(
                latest is not None
                and str(latest["action"]) == "confirmed"
                and current_oid is not None
                and str(latest["content_oid"]) == current_oid
            )
            results.append(
                {
                    "paper_id": str(paper["id"]),
                    "title": paper["title"],
                    "sidecar_path": paper["sidecar_path"],
                    "controls_valid": controls_valid,
                    "current_content_oid": current_oid,
                    "confirmed_current_version": confirmed_current,
                    "latest_event": dict(latest) if latest is not None else None,
                }
            )
    return {"ok": True, "papers": results}
