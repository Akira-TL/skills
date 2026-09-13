from __future__ import annotations

import argparse

from skill_manager import (
    SkillInstallError,
    doctor,
    install_from_source,
    inspect_source,
    list_installed,
    remove_installed,
    update_installed,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Akira machine-level Git + symlink Skill installer."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="只读取 GitHub source 中可用 Skill，不安装")
    inspect.add_argument("source", help="GitHub repository URL")
    inspect.add_argument("--ref", default="main")

    install = sub.add_parser("install", help="从 GitHub source 安装到 ~/.agents/skills")
    install.add_argument("source", help="GitHub repository URL")
    install.add_argument("--skill", action="append", default=[])
    install.add_argument("--all", dest="install_all", action="store_true")
    install.add_argument(
        "--root",
        action="append",
        default=[],
        help="与 --all 一起使用，只安装 source 中该相对目录下的 Skill；可重复",
    )
    install.add_argument("--ref", default="main")

    update = sub.add_parser("update", help="更新机器级已安装 Skill 的 Git source")
    update.add_argument("--source", help="只更新该 GitHub source")

    remove = sub.add_parser("remove", help="删除机器级受管 Skill 软链接，不删除 source checkout")
    remove.add_argument("skills", nargs="*")
    remove.add_argument("--source", help="删除该 GitHub source 登记的全部 Skill")

    sub.add_parser("list", help="列出 ~/.agents/skills 中的 Akira-managed Skill")
    sub.add_parser("doctor", help="检查机器级 source、manifest 与软链接是否一致")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "inspect":
        for name, path in inspect_source(args.source, args.ref):
            print(f"{name}\t{path}")
        return 0

    if args.command == "install":
        installed = install_from_source(
            args.source,
            skill_names=args.skill,
            install_all=args.install_all,
            include_roots=args.root,
            ref=args.ref,
        )
        print("INSTALLED " + ", ".join(installed))
        return 0

    if args.command == "update":
        updated = update_installed(repository=args.source)
        print("UPDATED " + (", ".join(updated) if updated else "none"))
        return 0

    if args.command == "remove":
        if not args.skills and not args.source:
            raise SkillInstallError("remove 需要 Skill 名称或 --source")
        removed = remove_installed(args.skills, repository=args.source)
        print("REMOVED " + (", ".join(removed) if removed else "none"))
        return 0

    if args.command == "list":
        for name, repository, commit in list_installed():
            print(f"{name}\t{repository}\t{commit}")
        return 0

    if args.command == "doctor":
        checked = doctor()
        print("OK " + (", ".join(checked) if checked else "no managed skills"))
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SkillInstallError as exc:
        raise SystemExit(f"ERROR {exc}") from exc
