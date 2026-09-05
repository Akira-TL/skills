from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from research_db_support.storage import ResearchDbError


BARE_ENGLISH_TERMS_IN_CHINESE_RESEARCH_TEXT = {
    "treatment",
    "outcome",
    "provenance",
    "confirmatory",
    "exploratory",
    "sensitivity",
    "pairwise",
    "claim",
    "dataset",
    "analysis",
    "artifact",
    "raw",
    "curated",
    "freeze",
    "randomization",
}

BARE_ENGLISH_TERMS_IN_CHINESE_COMMUNICATION = BARE_ENGLISH_TERMS_IN_CHINESE_RESEARCH_TEXT


def project_uses_chinese_research_text(project_root: Path) -> bool:
    research_path = project_root / "RESEARCH.md"
    if not research_path.exists():
        return False
    text = research_path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"[\u3400-\u9fff]", text)) >= 50


def academic_language_blockers_for_path(
    project_root: Path,
    path: Path,
    *,
    communication: bool = False,
    ignored_paragraphs: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not path.exists() or path.suffix.casefold() not in {".md", ".txt"}:
        return []

    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    blockers: list[dict[str, Any]] = []
    try:
        relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        relative_path = str(path)

    for index, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
        stripped = paragraph.strip()
        if not stripped or stripped.startswith("#") and "\n" not in stripped:
            continue
        if ignored_paragraphs and stripped in ignored_paragraphs:
            continue
        prose = re.sub(r"`[^`]*`", "", stripped)
        prose = re.sub(r"https?://\S+", "", prose)
        cjk_count = len(re.findall(r"[\u3400-\u9fff]", prose))
        english_words = re.findall(r"\b[A-Za-z][A-Za-z'-]{1,}\b", prose)
        if len(english_words) >= 30 and cjk_count < 5:
            blockers.append(
                {
                    "reason": "english_prose_in_chinese_research_text",
                    "path": relative_path,
                    "paragraph": index,
                    "english_word_count": len(english_words),
                    "preview": " ".join(stripped.split())[:180],
                }
            )

        term_check_prose = re.sub(r"（[^）]*[A-Za-z][^）]*）", "", prose)
        term_check_prose = re.sub(r"\([^)]*[A-Za-z][^)]*\)", "", term_check_prose)
        found_terms = sorted(
            term
            for term in BARE_ENGLISH_TERMS_IN_CHINESE_RESEARCH_TEXT
            if re.search(rf"\b{re.escape(term)}\b", term_check_prose, flags=re.IGNORECASE)
        )
        if found_terms:
            blockers.append(
                {
                    "reason": (
                        "bare_english_term_in_chinese_communication"
                        if communication
                        else "bare_english_term_in_chinese_research_text"
                    ),
                    "path": relative_path,
                    "paragraph": index,
                    "terms": found_terms,
                    "preview": " ".join(stripped.split())[:180],
                }
            )
    return blockers


def _require_academic_language_preflight(
    project_root: Path,
    paths: Iterable[Path],
    *,
    object_label: str,
    stage_label: str,
    remedy: str,
) -> None:
    if not project_uses_chinese_research_text(project_root):
        return
    blockers: list[dict[str, Any]] = []
    for path in dict.fromkeys(paths):
        blockers.extend(academic_language_blockers_for_path(project_root, path))
    if blockers:
        first = blockers[0]
        raise ResearchDbError(
            f"{object_label} {stage_label}学术语言检查失败：{first['path']} 第 {first['paragraph']} 段；"
            + remedy
        )


def require_academic_language_before_freeze(
    project_root: Path,
    paths: Iterable[Path],
    *,
    object_label: str,
) -> None:
    _require_academic_language_preflight(
        project_root,
        paths,
        object_label=object_label,
        stage_label="冻结前",
        remedy="请在 freeze 前修正人类科研正文，避免结果后再改写冻结 artifact。",
    )


def require_academic_language_before_execution(
    project_root: Path,
    paths: Iterable[Path],
    *,
    object_label: str,
) -> None:
    _require_academic_language_preflight(
        project_root,
        paths,
        object_label=object_label,
        stage_label="执行前",
        remedy="请在运行分析代码前修正人类科研正文，不要把语言修订留到结果可见之后。",
    )
