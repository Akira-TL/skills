from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from research_db_support.schema import ACADEMIC_LANGUAGE_LEGACY_BASELINE_META_KEY
from research_db_support.storage import connect, database_path
from .git import commit_has_path, path_changed_after, run_git
from .state import CURRENT_LOOPS

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

# Backward-compatible alias for callers that imported the older, narrower name.
BARE_ENGLISH_TERMS_IN_CHINESE_COMMUNICATION = BARE_ENGLISH_TERMS_IN_CHINESE_RESEARCH_TEXT


def canonical_paths(project_root: Path) -> list[str]:
    paths = {"RESEARCH.md", ".research/research.sqlite"}
    db_path = database_path(project_root)
    if not db_path.exists():
        return sorted(paths)

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for row in connection.execute("SELECT path FROM artifacts ORDER BY id"):
            path = Path(str(row["path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            paths.add(path.as_posix())
        for row in connection.execute(
            "SELECT sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
        ):
            path = Path(str(row["sidecar_path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            paths.add(path.as_posix())
        if "datasets" in tables:
            for row in connection.execute("SELECT provenance_path FROM datasets ORDER BY id"):
                paths.add(Path(str(row["provenance_path"])).as_posix())
        if "dataset_artifacts" in tables:
            for row in connection.execute(
                """
                SELECT location FROM dataset_artifacts
                WHERE storage_kind = 'local' AND git_tracking = 'required'
                ORDER BY id
                """
            ):
                paths.add(Path(str(row["location"])).as_posix())
        if "analysis_runs" in tables:
            for row in connection.execute("SELECT analysis_path, code_path FROM analysis_runs ORDER BY id"):
                paths.add(Path(str(row["analysis_path"])).as_posix())
                paths.add(Path(str(row["code_path"])).as_posix())
        if "analysis_artifacts" in tables:
            for row in connection.execute(
                "SELECT path FROM analysis_artifacts WHERE git_tracking = 'required' ORDER BY id"
            ):
                paths.add(Path(str(row["path"])).as_posix())
        if "hypothesis_sets" in tables:
            for row in connection.execute("SELECT artifact_path FROM hypothesis_sets ORDER BY id"):
                paths.add(Path(str(row["artifact_path"])).as_posix())
        if "research_designs" in tables:
            for row in connection.execute("SELECT artifact_path FROM research_designs ORDER BY id"):
                paths.add(Path(str(row["artifact_path"])).as_posix())
        if "studies" in tables:
            for row in connection.execute("SELECT provenance_path FROM studies ORDER BY id"):
                paths.add(Path(str(row["provenance_path"])).as_posix())
        if "study_artifacts" in tables:
            for row in connection.execute(
                """
                SELECT location FROM study_artifacts
                WHERE storage_kind = 'local' AND git_tracking = 'required'
                ORDER BY id
                """
            ):
                paths.add(Path(str(row["location"])).as_posix())
        if "communication_artifacts" in tables:
            for row in connection.execute(
                "SELECT path FROM communication_artifacts WHERE git_tracking = 'required' ORDER BY id"
            ):
                paths.add(Path(str(row["path"])).as_posix())
    return sorted(paths)


def _academic_language_paths(project_root: Path) -> list[Path]:
    paths = [project_root / "RESEARCH.md"]
    db_path = database_path(project_root)
    if not db_path.exists():
        return paths
    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for row in connection.execute(
            "SELECT sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
        ):
            path = Path(str(row["sidecar_path"]))
            if not path.is_absolute():
                path = project_root / path
            paths.append(path)
        if "datasets" in tables:
            for row in connection.execute("SELECT provenance_path FROM datasets ORDER BY id"):
                path = Path(str(row["provenance_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "analysis_runs" in tables:
            for row in connection.execute("SELECT analysis_path FROM analysis_runs ORDER BY id"):
                path = Path(str(row["analysis_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "analysis_artifacts" in tables:
            for row in connection.execute("SELECT path FROM analysis_artifacts ORDER BY id"):
                path = Path(str(row["path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "hypothesis_sets" in tables:
            for row in connection.execute("SELECT artifact_path FROM hypothesis_sets ORDER BY id"):
                path = Path(str(row["artifact_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "research_designs" in tables:
            for row in connection.execute("SELECT artifact_path FROM research_designs ORDER BY id"):
                path = Path(str(row["artifact_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "studies" in tables:
            for row in connection.execute("SELECT provenance_path FROM studies ORDER BY id"):
                path = Path(str(row["provenance_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "study_artifacts" in tables:
            for row in connection.execute(
                "SELECT location FROM study_artifacts WHERE storage_kind = 'local' ORDER BY id"
            ):
                path = Path(str(row["location"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "communication_artifacts" in tables:
            for row in connection.execute(
                """
                SELECT path FROM communication_artifacts
                WHERE role IN ('title_abstract', 'methods', 'results', 'discussion', 'figure_legend', 'lay_summary', 'traceability', 'other')
                ORDER BY id
                """
            ):
                path = Path(str(row["path"]))
                paths.append(path if path.is_absolute() else project_root / path)
    return list(dict.fromkeys(paths))


def _legacy_language_baseline_commit(project_root: Path) -> str | None:
    db_path = database_path(project_root)
    if not db_path.exists():
        return None
    with connect(db_path) as connection:
        try:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = ?",
                (ACADEMIC_LANGUAGE_LEGACY_BASELINE_META_KEY,),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    value = str(row["value"]).strip() if row else ""
    return value or None


def _path_is_unchanged_legacy_text(
    project_root: Path,
    path: Path,
    baseline_commit: str | None,
) -> bool:
    if not baseline_commit:
        return False
    try:
        relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return False
    if run_git(
        project_root, "merge-base", "--is-ancestor", baseline_commit, "HEAD"
    ).returncode != 0:
        return False
    if not commit_has_path(project_root, baseline_commit, relative_path):
        return False
    if path_changed_after(project_root, baseline_commit, relative_path):
        return False
    return run_git(
        project_root, "diff", "--quiet", baseline_commit, "--", relative_path
    ).returncode == 0


def academic_language_readiness(project_root: Path) -> dict[str, Any]:
    research_path = project_root / "RESEARCH.md"
    if not research_path.exists():
        return {"ready": True, "checked": False, "blockers": []}
    research_text = research_path.read_text(encoding="utf-8", errors="ignore")
    if len(re.findall(r"[\u3400-\u9fff]", research_text)) < 50:
        return {"ready": True, "checked": False, "blockers": []}

    blockers: list[dict[str, Any]] = []
    legacy_baseline_commit = _legacy_language_baseline_commit(project_root)
    grandfathered_paths: list[str] = []
    for path in _academic_language_paths(project_root):
        if not path.exists() or path.suffix.casefold() not in {".md", ".txt"}:
            continue
        if _path_is_unchanged_legacy_text(project_root, path, legacy_baseline_commit):
            grandfathered_paths.append(path.resolve().relative_to(project_root.resolve()).as_posix())
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for index, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
            stripped = paragraph.strip()
            if not stripped or stripped.startswith("#") and "\n" not in stripped:
                continue
            if stripped in CURRENT_LOOPS:
                continue
            prose_for_language_check = re.sub(r"`[^`]*`", "", stripped)
            prose_for_language_check = re.sub(r"https?://\S+", "", prose_for_language_check)
            cjk_count = len(re.findall(r"[\u3400-\u9fff]", prose_for_language_check))
            english_words = re.findall(r"\b[A-Za-z][A-Za-z'-]{1,}\b", prose_for_language_check)
            relative_path = str(path.relative_to(project_root))
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
            term_check_prose = re.sub(r"（[^）]*[A-Za-z][^）]*）", "", prose_for_language_check)
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
                            if relative_path.startswith("communication/")
                            else "bare_english_term_in_chinese_research_text"
                        ),
                        "path": relative_path,
                        "paragraph": index,
                        "terms": found_terms,
                        "preview": " ".join(stripped.split())[:180],
                    }
                )
    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "legacy_baseline_commit": legacy_baseline_commit,
        "grandfathered_paths": sorted(grandfathered_paths),
    }
