from __future__ import annotations

import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from research_db_support.academic_language import (
    academic_language_blockers_for_path,
    project_uses_chinese_research_text,
)
from research_db_support.schema import (
    ACADEMIC_LANGUAGE_LEGACY_BASELINE_META_KEY,
    latest_version,
)
from research_db_support.storage import connect, database_path
from .git import commit_has_path, path_changed_after, run_git
from .state import CURRENT_LOOPS

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
            for row in connection.execute(
                "SELECT path FROM analysis_artifacts WHERE role = 'other' ORDER BY id"
            ):
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


def _schema_version_at_commit(project_root: Path, commit: str) -> int | None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(project_root),
            "show",
            f"{commit}:.research/research.sqlite",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
        handle.write(result.stdout)
        handle.flush()
        try:
            with sqlite3.connect(handle.name) as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version:
                    return version
                row = connection.execute(
                    "SELECT value FROM meta WHERE key = 'schema_version'"
                ).fetchone()
                return int(row[0]) if row else None
        except (sqlite3.DatabaseError, ValueError, TypeError):
            return None


def _validate_legacy_language_baseline(
    project_root: Path,
    baseline_commit: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    if not baseline_commit:
        return None, None
    if run_git(
        project_root, "merge-base", "--is-ancestor", baseline_commit, "HEAD"
    ).returncode != 0:
        return None, {
            "reason": "academic_language_legacy_baseline_invalid",
            "baseline_commit": baseline_commit,
            "detail": "legacy baseline 不是当前 HEAD 的祖先。",
        }
    baseline_schema_version = _schema_version_at_commit(project_root, baseline_commit)
    current_schema_version = latest_version()
    if baseline_schema_version is None or baseline_schema_version >= current_schema_version:
        return None, {
            "reason": "academic_language_legacy_baseline_invalid",
            "baseline_commit": baseline_commit,
            "baseline_schema_version": baseline_schema_version,
            "current_schema_version": current_schema_version,
            "detail": (
                "legacy baseline 只允许由真实 schema migration 记录；baseline commit 中的数据库 "
                "schema 必须低于当前版本。"
            ),
        }
    return baseline_commit, None


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
    if not research_path.exists() or not project_uses_chinese_research_text(project_root):
        return {"ready": True, "checked": False, "blockers": []}

    blockers: list[dict[str, Any]] = []
    recorded_legacy_baseline_commit = _legacy_language_baseline_commit(project_root)
    legacy_baseline_commit, baseline_blocker = _validate_legacy_language_baseline(
        project_root, recorded_legacy_baseline_commit
    )
    if baseline_blocker is not None:
        blockers.append(baseline_blocker)
    grandfathered_paths: list[str] = []
    for path in _academic_language_paths(project_root):
        if not path.exists() or path.suffix.casefold() not in {".md", ".txt"}:
            continue
        if _path_is_unchanged_legacy_text(project_root, path, legacy_baseline_commit):
            grandfathered_paths.append(path.resolve().relative_to(project_root.resolve()).as_posix())
            continue
        relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
        blockers.extend(
            academic_language_blockers_for_path(
                project_root,
                path,
                communication=relative_path.startswith("communication/"),
                ignored_paragraphs=CURRENT_LOOPS,
            )
        )
    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "legacy_baseline_commit": recorded_legacy_baseline_commit,
        "legacy_baseline_valid": baseline_blocker is None,
        "grandfathered_paths": sorted(grandfathered_paths),
    }
