from __future__ import annotations

import subprocess
from pathlib import Path

def run_git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )



def commit_has_path(project_root: Path, commit: str, path: str) -> bool:
    result = run_git(project_root, "cat-file", "-e", f"{commit}:{path}")
    return result.returncode == 0


def path_changed_after(project_root: Path, commit: str, path: str) -> bool:
    result = run_git(project_root, "log", "--format=%H", f"{commit}..HEAD", "--", path)
    return result.returncode != 0 or bool(result.stdout.strip())


def first_path_change_after(project_root: Path, commit: str, path: str) -> str | None:
    result = run_git(
        project_root,
        "log",
        "--reverse",
        "--format=%H",
        f"{commit}..HEAD",
        "--",
        path,
    )
    if result.returncode != 0:
        return None
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)
