from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_db_support.storage import connect, database_path

BARE_ENGLISH_TERMS_IN_CHINESE_COMMUNICATION = {
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
        if "hypothesis_sets" in tables:
            for row in connection.execute("SELECT artifact_path FROM hypothesis_sets ORDER BY id"):
                path = Path(str(row["artifact_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "research_designs" in tables:
            for row in connection.execute("SELECT artifact_path FROM research_designs ORDER BY id"):
                path = Path(str(row["artifact_path"]))
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
    return paths


def academic_language_readiness(project_root: Path) -> dict[str, Any]:
    research_path = project_root / "RESEARCH.md"
    if not research_path.exists():
        return {"ready": True, "checked": False, "blockers": []}
    research_text = research_path.read_text(encoding="utf-8", errors="ignore")
    if len(re.findall(r"[\u3400-\u9fff]", research_text)) < 50:
        return {"ready": True, "checked": False, "blockers": []}

    blockers: list[dict[str, Any]] = []
    for path in _academic_language_paths(project_root):
        if not path.exists() or path.suffix.casefold() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for index, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
            stripped = paragraph.strip()
            if not stripped or stripped.startswith("#") and "\n" not in stripped:
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
            if relative_path.startswith("communication/"):
                communication_prose = re.sub(r"（[^）]*[A-Za-z][^）]*）", "", prose_for_language_check)
                communication_prose = re.sub(r"\([^)]*[A-Za-z][^)]*\)", "", communication_prose)
                found_terms = sorted(
                    term
                    for term in BARE_ENGLISH_TERMS_IN_CHINESE_COMMUNICATION
                    if re.search(rf"\b{re.escape(term)}\b", communication_prose, flags=re.IGNORECASE)
                )
                if found_terms:
                    blockers.append(
                        {
                            "reason": "bare_english_term_in_chinese_communication",
                            "path": relative_path,
                            "paragraph": index,
                            "terms": found_terms,
                            "preview": " ".join(stripped.split())[:180],
                        }
                    )
    return {"ready": not blockers, "checked": True, "blockers": blockers}
