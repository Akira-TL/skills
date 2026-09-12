from __future__ import annotations

import re
from typing import Any

from research_db_ops.user_reading import (
    BOTTOM_END,
    BOTTOM_START,
    TOP_END,
    TOP_START,
    USER_NOTES_END,
    USER_NOTES_START,
    parse_confirmation_controls,
)
from research_db_support.storage import ResearchDbError


NOTE_FORMAT_MARKER = "<!-- akira:literature-note:v1 -->"
METADATA_FIELDS = (
    "中文译题",
    "第一作者",
    "期刊 / 会议",
    "年份",
    "DOI",
    "PMID / PMCID",
    "Paper ID",
    "论文类型",
    "当前阅读用途",
    "本地全文",
)
REQUIRED_H2_HEADINGS = (
    "三句话总结",
    "为什么值得读",
    "论文逻辑",
    "方法拆解",
    "实验逻辑",
    "数据直接显示什么",
    "作者如何解释",
    "我们的证据评估",
    "关键图表与定位",
    "可复用内容",
    "科研启发",
    "结论边界",
    "我的笔记",
)

_H1_RE = re.compile(r"^# (?!#)(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^## (?!#)(.+?)\s*$", re.MULTILINE)
_METADATA_SEPARATOR_RE = re.compile(r"^\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|$")


def _strip_user_notes_content(text: str, *, required: bool) -> str:
    start_count = text.count(USER_NOTES_START)
    end_count = text.count(USER_NOTES_END)
    if start_count == 0 and end_count == 0 and not required:
        return text
    if start_count != 1 or end_count != 1:
        raise ResearchDbError("人类阅读 Markdown 的用户笔记区边界必须成对且只能出现一次。")
    start_index = text.find(USER_NOTES_START)
    end_index = text.find(USER_NOTES_END)
    if end_index <= start_index:
        raise ResearchDbError("人类阅读 Markdown 的用户笔记区边界顺序无效。")
    return text[: start_index + len(USER_NOTES_START)] + "\n" + text[end_index:]


def _metadata_rows(text: str, marker_end: int) -> tuple[dict[str, str], int]:
    tail = text[marker_end:].lstrip("\n")
    skipped = len(text[marker_end:]) - len(tail)
    lines = tail.splitlines(keepends=True)
    if len(lines) < 2 + len(METADATA_FIELDS):
        raise ResearchDbError("人类阅读 Markdown 文件头缺少固定书目信息表。")
    if lines[0].strip() != "| 项目 | 信息 |":
        raise ResearchDbError("人类阅读 Markdown 文件头必须使用固定书目信息表头 `| 项目 | 信息 |`。")
    if not _METADATA_SEPARATOR_RE.fullmatch(lines[1].strip()):
        raise ResearchDbError("人类阅读 Markdown 书目信息表缺少标准分隔行。")

    values: dict[str, str] = {}
    for index, expected in enumerate(METADATA_FIELDS, start=2):
        raw = lines[index].strip()
        if not (raw.startswith("|") and raw.endswith("|")):
            raise ResearchDbError(f"书目信息表缺少固定字段：{expected}")
        cells = raw[1:-1].split("|", 1)
        if len(cells) != 2:
            raise ResearchDbError(f"书目信息表字段格式无效：{expected}")
        label, value = (cell.strip() for cell in cells)
        if label != expected:
            raise ResearchDbError(f"书目信息表字段顺序无效：期望 `{expected}`，实际 `{label}`。")
        if not value:
            raise ResearchDbError(f"书目信息表字段不得留空：{expected}；未知或不适用时应显式写明。")
        values[label] = value

    consumed = sum(len(line) for line in lines[: 2 + len(METADATA_FIELDS)])
    return values, marker_end + skipped + consumed


def validate_human_literature_note(text: str) -> dict[str, Any]:
    """Validate one human-facing literature Markdown note.

    Notes created before the versioned human-note contract remain legacy-compatible.
    Any note using the modern user-notes block must opt into the v1 marker and then
    satisfy the complete fixed structure.
    """
    parse_confirmation_controls(text)

    marker_count = text.count(NOTE_FORMAT_MARKER)
    has_user_notes = USER_NOTES_START in text or USER_NOTES_END in text
    if marker_count == 0:
        if has_user_notes:
            raise ResearchDbError(
                "包含用户专属笔记区的人类阅读 Markdown 必须声明 `akira:literature-note:v1` 格式。"
            )
        return {"format": "legacy"}
    if marker_count != 1:
        raise ResearchDbError("人类阅读 Markdown 格式标记必须且只能出现一次。")

    normalized = _strip_user_notes_content(text, required=True)
    h1_matches = list(_H1_RE.finditer(normalized))
    if len(h1_matches) != 1:
        raise ResearchDbError("v1 人类阅读 Markdown 必须且只能包含一个一级标题作为原始论文题名。")
    first_nonblank = next((line.strip() for line in normalized.splitlines() if line.strip()), "")
    if not first_nonblank.startswith("# ") or first_nonblank.startswith("## "):
        raise ResearchDbError("v1 人类阅读 Markdown 的第一项内容必须是 `# 原始论文题名`。")
    title = h1_matches[0].group(1).strip()
    if not title:
        raise ResearchDbError("人类阅读 Markdown 的原始论文题名不得为空。")

    marker_index = normalized.find(NOTE_FORMAT_MARKER)
    if marker_index <= h1_matches[0].end():
        raise ResearchDbError("`akira:literature-note:v1` 格式标记必须位于一级标题之后。")
    if normalized[h1_matches[0].end():marker_index].strip():
        raise ResearchDbError("一级标题与 `akira:literature-note:v1` 格式标记之间不得插入其他内容。")
    metadata, metadata_end = _metadata_rows(normalized, marker_index + len(NOTE_FORMAT_MARKER))

    top_index = normalized.find(TOP_START)
    bottom_index = normalized.find(BOTTOM_START)
    if top_index < metadata_end:
        raise ResearchDbError("顶部阅读确认框必须位于固定书目信息表之后。")
    if normalized[metadata_end:top_index].strip():
        raise ResearchDbError("固定书目信息表与顶部阅读确认框之间不得插入其他字段或正文。")

    h2_headings = [match.group(1).strip() for match in _H2_RE.finditer(normalized)]
    if tuple(h2_headings) != REQUIRED_H2_HEADINGS:
        raise ResearchDbError(
            "v1 人类阅读 Markdown 的二级标题必须固定且按规定顺序出现："
            + " → ".join(REQUIRED_H2_HEADINGS)
        )
    first_h2_index = normalized.find("## " + REQUIRED_H2_HEADINGS[0])
    if not (metadata_end <= top_index < first_h2_index):
        raise ResearchDbError("顶部阅读确认框必须位于书目信息表与 `## 三句话总结` 之间。")
    top_end_index = normalized.find(TOP_END)
    if top_end_index < top_index or normalized[top_end_index + len(TOP_END):first_h2_index].strip():
        raise ResearchDbError("顶部阅读确认框后应直接进入 `## 三句话总结`。")

    user_notes_heading = normalized.find("## 我的笔记")
    user_notes_start = normalized.find(USER_NOTES_START)
    user_notes_end = normalized.find(USER_NOTES_END)
    if not (user_notes_heading < user_notes_start < user_notes_end < bottom_index):
        raise ResearchDbError("用户专属笔记区必须位于 `## 我的笔记` 下，并在底部阅读确认框之前。")
    bottom_end_index = normalized.find(BOTTOM_END)
    if bottom_end_index < bottom_index or normalized[bottom_end_index + len(BOTTOM_END):].strip():
        raise ResearchDbError("底部阅读确认框必须是 v1 人类阅读 Markdown 的最后一个结构块。")

    return {
        "format": "v1",
        "title": title,
        "metadata": metadata,
        "headings": list(REQUIRED_H2_HEADINGS),
    }
