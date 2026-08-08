from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STABLE_CATEGORIES = {"engineering", "productivity"}
LIFECYCLE_CATEGORIES = {"in-progress", "deprecated"}
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def ok(message: str) -> None:
    print(f"OK    {message}")


def fail(message: str) -> None:
    print(f"FAIL  {message}")


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    try:
        _, block, _ = text.split("---", 2)
    except ValueError:
        return {}

    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"\'')
    return result


def skill_files() -> list[Path]:
    files: list[Path] = []
    for category in sorted(STABLE_CATEGORIES | LIFECYCLE_CATEGORIES):
        root = REPO_ROOT / category
        if not root.is_dir():
            continue
        files.extend(sorted(root.glob("*/SKILL.md")))
    return files


def check_skills() -> int:
    failed = False
    names: Counter[str] = Counter()

    for skill_file in skill_files():
        relative = skill_file.relative_to(REPO_ROOT)
        category = relative.parts[0]
        directory_name = skill_file.parent.name
        metadata = parse_frontmatter(skill_file)
        name = metadata.get("name", "")
        description = metadata.get("description", "")

        if NAME_RE.fullmatch(directory_name) is None:
            fail(f"{relative}: 目录名不是 lowercase kebab-case")
            failed = True
        if name != directory_name:
            fail(f"{relative}: frontmatter name={name!r} 与目录名不一致")
            failed = True
        if not description:
            fail(f"{relative}: 缺少 description")
            failed = True
        if name:
            names[name] += 1

        if category in STABLE_CATEGORIES:
            doc = REPO_ROOT / "docs" / category / f"{directory_name}.md"
            if not doc.is_file():
                fail(f"{relative}: 稳定 Skill 缺少 {doc.relative_to(REPO_ROOT)}")
                failed = True

    for name, count in sorted(names.items()):
        if count > 1:
            fail(f"Skill name 重复：{name} × {count}")
            failed = True

    if not skill_files():
        fail("仓库中没有发现 SKILL.md")
        failed = True

    for doc in sorted((REPO_ROOT / "docs").glob("*/*.md")):
        relative = doc.relative_to(REPO_ROOT)
        category = relative.parts[1]
        if category not in STABLE_CATEGORIES:
            continue
        skill = REPO_ROOT / category / doc.stem / "SKILL.md"
        if not skill.is_file():
            fail(f"{relative}: 没有对应的 {skill.relative_to(REPO_ROOT)}")
            failed = True

    if not failed:
        ok(f"Skill 结构与文档映射正常，共 {len(skill_files())} 个 Skill")
    return 1 if failed else 0


def check_repository() -> int:
    failed = False
    for required in ("AGENTS.md", "README.md", "scripts/guard.py"):
        path = REPO_ROOT / required
        if path.is_file():
            ok(required)
        else:
            fail(f"缺少 {required}")
            failed = True
    return 1 if failed else 0


def report_git_structure() -> None:
    branch = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "branch", "-vv"],
        capture_output=True,
        text=True,
    )
    worktree = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "list"],
        capture_output=True,
        text=True,
    )
    print("INFO  本地分支：")
    print(branch.stdout.rstrip() or "(none)")
    print("INFO  worktree：")
    print(worktree.stdout.rstrip() or "(none)")


def cmd_skills(_: argparse.Namespace) -> int:
    return check_skills()


def cmd_check(_: argparse.Namespace) -> int:
    failed = bool(check_repository())
    failed = bool(check_skills()) or failed
    report_git_structure()
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Akira Skills 仓库机械检查")
    subparsers = parser.add_subparsers(dest="command", required=True)
    skills = subparsers.add_parser("skills", help="检查 Skill 结构")
    skills.set_defaults(func=cmd_skills)
    check = subparsers.add_parser("check", help="运行仓库完整机械检查")
    check.set_defaults(func=cmd_check)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
