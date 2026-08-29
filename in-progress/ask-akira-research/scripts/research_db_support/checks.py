from __future__ import annotations

import re
import sqlite3
from pathlib import Path


def main_text_exposes_code_data_locator(
    project_root: Path, connection: sqlite3.Connection, paper_id: str
) -> bool:
    """Detect a narrow, explicit data/code locator in machine-readable main text."""
    rows = connection.execute(
        "SELECT path FROM artifacts WHERE paper_id = ? AND kind = 'main_text' ORDER BY id",
        (paper_id,),
    ).fetchall()
    heading_patterns = (
        "availability of data and materials",
        "data availability",
        "code availability",
        "availability of data",
    )
    for row in rows:
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = project_root / path
        if path.suffix.casefold() not in {".xml", ".html", ".htm", ".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text[:6_000_000].casefold()
        for heading in heading_patterns:
            for match in re.finditer(re.escape(heading), lowered):
                window = lowered[match.start() : match.start() + 5000]
                has_locator = bool(
                    re.search(r"https?://|href\s*=|doi:\s*10\.|accession|repository", window)
                )
                has_availability_signal = any(
                    phrase in window
                    for phrase in (
                        "available at",
                        "available from",
                        "publicly available",
                        "freely available",
                        "deposited",
                        "repository",
                        "accession",
                    )
                )
                if has_locator and has_availability_signal:
                    return True
    return False


def source_locator_is_specific(value: object) -> bool:
    if value is None:
        return False
    normalized = " ".join(str(value).strip().casefold().split())
    if not normalized:
        return False
    generic = {
        "abstract",
        "introduction",
        "methods",
        "materials and methods",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "main text",
        "supplement",
        "supplementary material",
        "supplementary materials",
        "supplementary information",
    }
    return normalized not in generic
