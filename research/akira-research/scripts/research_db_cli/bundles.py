from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from research_db_support.storage import ResearchDbError
from .project import PROJECT_BUNDLE_DEFAULTS


BUNDLE_DEFAULTS = {
    "record-search": "search.json",
    "record-access-attempt": "access-attempt.json",
    "update-candidate": "candidate-update.json",
    "relate": "relation.json",
    "add-paper-artifacts": "paper-artifacts.json",
    "ingest-paper": "paper.json",
    "ingest-reading": "reconstruction.json",
    "ingest-critical": "critical.json",
    "record-dataset": "dataset.json",
    "record-analysis": "analysis.json",
    **PROJECT_BUNDLE_DEFAULTS,
    "record-hypothesis-proposal": "hypothesis-proposal.json",
    "record-user-hypothesis-decision": "user-hypothesis-decision.json",
    "record-research-judgment": "research-judgment.json",
    "record-hypothesis-set": "hypothesis-set.json",
    "record-design": "design.json",
    "record-hypothesis-evaluation": "hypothesis-evaluation.json",
    "record-communication": "communication.json",
}


def bundle_directory(project_root: Path) -> Path:
    return project_root / ".research" / "bundles"


def bundle_path(
    project_root: Path,
    command: str,
    path_value: str | None,
) -> Path | None:
    if path_value == "-":
        return None
    if path_value is None:
        return bundle_directory(project_root) / BUNDLE_DEFAULTS[command]

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def load_json_object(
    project_root: Path,
    command: str,
    path_value: str | None,
) -> dict[str, Any]:
    path = bundle_path(project_root, command, path_value)
    if path is None:
        raw = json.load(sys.stdin)
    else:
        if not path.is_file():
            raise ResearchDbError(f"bundle 文件不存在：{path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ResearchDbError("bundle 输入必须是 JSON object。")
    return raw
