from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REQUIRED_RESEARCH_SECTIONS = (
    "Objective",
    "Current Loop",
    "Active Uncertainty",
    "Current State",
    "Active Work",
    "Open Threads",
    "Key Decisions",
    "References",
)

CURRENT_LOOPS = {
    "EXPLORE",
    "QUESTION",
    "HYPOTHESIS",
    "DESIGN",
    "DATA",
    "ANALYSIS",
    "INTERPRETATION",
    "COMMUNICATION",
}

_STALE_COMPLETION_MARKERS = (
    "bootstrap",
    "validate --completion",
    "research-db validate",
    "completion validation",
    "completion gate",
    "clean-tree",
    "git commit",
    "git tracking",
)

_EVIDENCE_STATUS_EXPLANATION_MARKERS = (
    "尚无证据",
    "证据不足",
    "当前证据不能",
    "当前无法判断",
    "尚无法判断",
    "不足以区分",
    "不能识别",
    "无法识别",
    "尚未设计",
    "尚未形成设计",
)


def _sections(text: str) -> dict[str, str]:
    headings = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def _evidence_status_competing_explanations(active_uncertainty: str) -> list[dict[str, Any]]:
    match = re.search(
        r"(?ims)^Competing explanations:\s*(.*?)(?=^\s*(?:Discriminating gap|Best next evidence|Question):|\Z)",
        active_uncertainty,
    )
    if match is None:
        return []

    invalid: list[dict[str, Any]] = []
    for line in match.group(1).splitlines():
        explanation = line.strip()
        if not re.match(r"^[-*]\s+", explanation):
            continue
        markers = [
            marker
            for marker in _EVIDENCE_STATUS_EXPLANATION_MARKERS
            if marker in explanation
        ]
        if markers:
            invalid.append({"explanation": explanation, "markers": markers})
    return invalid


def project_state_readiness(project_root: Path) -> dict[str, Any]:
    path = project_root / "RESEARCH.md"
    if not path.exists():
        return {
            "ready": False,
            "checked": True,
            "blockers": [{"reason": "research_state_missing_file"}],
        }

    sections = _sections(path.read_text(encoding="utf-8", errors="ignore"))
    blockers: list[dict[str, Any]] = []
    missing = [name for name in REQUIRED_RESEARCH_SECTIONS if name not in sections]
    if missing:
        blockers.append({"reason": "research_state_missing_sections", "sections": missing})

    current_loop = sections.get("Current Loop", "").strip()
    if "Current Loop" in sections and current_loop not in CURRENT_LOOPS:
        blockers.append(
            {
                "reason": "research_state_invalid_current_loop",
                "current_loop": current_loop,
            }
        )

    active_uncertainty = sections.get("Active Uncertainty", "").strip()
    evidence_status_explanations = _evidence_status_competing_explanations(active_uncertainty)
    if evidence_status_explanations:
        markers = sorted(
            {
                marker
                for item in evidence_status_explanations
                for marker in item["markers"]
            }
        )
        blockers.append(
            {
                "reason": "research_state_competing_explanation_is_evidence_status",
                "markers": markers,
                "explanations": evidence_status_explanations,
            }
        )

    active_work = sections.get("Active Work", "").strip()
    if "Active Work" in sections and not active_work:
        blockers.append({"reason": "research_state_active_work_empty"})
    elif active_work:
        normalized = " ".join(active_work.casefold().split())
        markers = [marker for marker in _STALE_COMPLETION_MARKERS if marker in normalized]
        if markers:
            blockers.append(
                {
                    "reason": "research_state_active_work_stale_completion",
                    "markers": markers,
                }
            )

    return {
        "ready": not blockers,
        "checked": True,
        "blockers": blockers,
        "current_loop": current_loop or None,
    }
