from __future__ import annotations

from pathlib import Path
from typing import Any

from research_db_validation import validate
from research_db_ops.candidates import discovery_readiness
from .git import _git
from .language import _canonical_paths, academic_language_readiness
from .literature import literature_completion_readiness
from .project import (
    communication_completion_readiness,
    downstream_completion_readiness,
    planning_completion_readiness,
)
from .messages import (
    append_academic_language_errors,
    append_communication_errors,
    append_downstream_errors,
    append_literature_errors,
    append_planning_errors,
)

def validate_completion(project_root: Path) -> dict[str, Any]:
    base = validate(project_root)
    errors = list(base["errors"])
    warnings = list(base["warnings"])

    readiness = discovery_readiness(project_root)
    if readiness["has_discovery"] and not readiness["ready_for_saturation"]:
        reasons = ", ".join(
            str(blocker.get("reason", "unknown")) for blocker in readiness["blockers"]
        )
        errors.append(
            "Discovery Candidate 队列尚未闭合，不能作为完成状态或声称 practical conceptual saturation："
            + reasons
        )

    literature = literature_completion_readiness(project_root, readiness)
    append_literature_errors(errors, literature["blockers"])
    downstream = downstream_completion_readiness(project_root)
    append_downstream_errors(errors, downstream["blockers"])
    planning = planning_completion_readiness(project_root)
    append_planning_errors(errors, planning["blockers"])
    communication = communication_completion_readiness(project_root)
    append_communication_errors(errors, communication["blockers"])
    academic_language = academic_language_readiness(project_root)
    append_academic_language_errors(errors, academic_language["blockers"])
    git_info: dict[str, Any] = {
        "repository_root": None,
        "head": None,
        "canonical_paths": [],
        "dirty_canonical_paths": [],
    }
    top = _git(project_root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        errors.append("科研项目尚不是 Git repository；不能完成科研 provenance gate。")
    else:
        repo_root = Path(top.stdout.strip()).resolve()
        git_info["repository_root"] = str(repo_root)
        if repo_root != project_root.resolve():
            errors.append(
                f"科研项目根目录不是独立 Git repository top-level：{repo_root}。"
            )

        head = _git(project_root, "rev-parse", "--verify", "HEAD")
        if head.returncode != 0:
            errors.append("科研项目尚无任何 Git commit；研究状态没有形成版本历史。")
        else:
            git_info["head"] = head.stdout.strip()

        canonical_paths = _canonical_paths(project_root)
        git_info["canonical_paths"] = canonical_paths
        for path in canonical_paths:
            tracked = _git(project_root, "ls-files", "--error-unmatch", "--", path)
            if tracked.returncode != 0:
                errors.append(f"canonical research artifact 尚未被 Git 跟踪：{path}")

        if canonical_paths:
            status = _git(
                project_root,
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *canonical_paths,
            )
            dirty = [line for line in status.stdout.splitlines() if line.strip()]
            git_info["dirty_canonical_paths"] = dirty
            if dirty:
                errors.append("canonical research artifacts 仍有未提交修改：" + " | ".join(dirty))

    completion_passed = not errors
    return {
        "ok": completion_passed,
        "completion_checked": True,
        "completion": completion_passed,
        "database": base["database"],
        "errors": errors,
        "warnings": warnings,
        "discovery": readiness,
        "literature": literature,
        "downstream": downstream,
        "planning": planning,
        "communication": communication,
        "academic_language": academic_language,
        "git": git_info,
    }
