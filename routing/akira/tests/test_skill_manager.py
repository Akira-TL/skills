from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import skill_manager
import skills as skills_cli


class SourceIdentityTests(unittest.TestCase):
    def test_normalize_github_https_and_ssh(self) -> None:
        expected = ("Akira-TL", "skills", "https://github.com/Akira-TL/skills.git")
        self.assertEqual(
            skill_manager.normalize_github_source("https://github.com/Akira-TL/skills.git"),
            expected,
        )
        self.assertEqual(
            skill_manager.normalize_github_source("git@github.com:Akira-TL/skills.git"),
            expected,
        )

    def test_non_github_source_is_rejected(self) -> None:
        with self.assertRaises(skill_manager.SkillInstallError):
            skill_manager.normalize_github_source("https://example.com/org/repo.git")


class InstallTests(unittest.TestCase):
    def _fixture_checkout(self, root: Path, dirname: str = "checkout") -> Path:
        checkout = root / dirname
        fixtures = {
            "alpha": checkout / "skills" / "engineering" / "alpha",
            "beta": checkout / "skills" / "productivity" / "beta",
            "ask-akira": checkout / "skills" / "in-progress" / "ask-akira",
            "misc-one": checkout / "skills" / "misc" / "misc-one",
        }
        for name, directory in fixtures.items():
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: fixture\n---\n",
                encoding="utf-8",
            )
        return checkout

    def _patch_machine_paths(self, root: Path):
        return (
            mock.patch.object(skill_manager, "GLOBAL_SKILLS", root / ".agents" / "skills"),
            mock.patch.object(
                skill_manager, "GLOBAL_MANIFEST", root / ".agents" / "akira-skills.json"
            ),
            mock.patch.object(skill_manager, "SOURCES_ROOT", root / ".agents" / "sources"),
        )

    def test_discovery_skips_deprecated(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            active = root / "skills" / "active" / "SKILL.md"
            active.parent.mkdir(parents=True)
            active.write_text("---\nname: active\n---\n", encoding="utf-8")
            deprecated = root / "deprecated" / "old" / "SKILL.md"
            deprecated.parent.mkdir(parents=True)
            deprecated.write_text("---\nname: old\n---\n", encoding="utf-8")

            self.assertEqual(skill_manager.discover_skills(root), {"active": active.parent})

    def test_install_registers_machine_symlink_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            checkout = self._fixture_checkout(root)
            source = "https://github.com/Akira-TL/example.git"
            patches = self._patch_machine_paths(root)
            with ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "ensure_source_checkout",
                        return_value=(checkout, "abc123", source),
                    )
                )
                installed = skill_manager.install_from_source(source, skill_names=["alpha"])

            self.assertEqual(installed, ["alpha"])
            link = root / ".agents" / "skills" / "alpha"
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                skill_manager.direct_link_target(link),
                (checkout / "skills" / "engineering" / "alpha").absolute(),
            )
            manifest = json.loads(
                (root / ".agents" / "akira-skills.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["scope"], "machine")
            self.assertEqual(manifest["skills"]["alpha"]["commit"], "abc123")
            self.assertEqual(
                set(manifest["skills"]["alpha"]),
                {"repository", "ref", "commit", "source_path"},
            )

    def test_all_can_be_limited_by_roots_and_extended_by_explicit_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            checkout = self._fixture_checkout(root)
            source = "https://github.com/Akira-TL/example.git"
            patches = self._patch_machine_paths(root)
            with ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "ensure_source_checkout",
                        return_value=(checkout, "abc123", source),
                    )
                )
                installed = skill_manager.install_from_source(
                    source,
                    skill_names=["ask-akira"],
                    install_all=True,
                    include_roots=["skills/engineering", "skills/productivity"],
                )

            self.assertEqual(installed, ["alpha", "ask-akira", "beta"])
            self.assertFalse((root / ".agents" / "skills" / "misc-one").exists())

    def test_machine_name_conflict_from_other_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            first = self._fixture_checkout(root, "first")
            second = self._fixture_checkout(root, "second")
            first_source = "https://github.com/Akira-TL/first.git"
            second_source = "https://github.com/Akira-TL/second.git"
            patches = self._patch_machine_paths(root)
            with ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                with mock.patch.object(
                    skill_manager,
                    "ensure_source_checkout",
                    return_value=(first, "first123", first_source),
                ):
                    skill_manager.install_from_source(first_source, skill_names=["alpha"])
                with mock.patch.object(
                    skill_manager,
                    "ensure_source_checkout",
                    return_value=(second, "second123", second_source),
                ):
                    with self.assertRaises(skill_manager.SkillInstallError):
                        skill_manager.install_from_source(second_source, skill_names=["alpha"])

            self.assertEqual(
                skill_manager.direct_link_target(root / ".agents" / "skills" / "alpha"),
                (first / "skills" / "engineering" / "alpha").absolute(),
            )

    def test_doctor_rejects_unmanaged_registry_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            checkout = self._fixture_checkout(root)
            source = "https://github.com/Akira-TL/example.git"
            patches = self._patch_machine_paths(root)
            with ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "ensure_source_checkout",
                        return_value=(checkout, "abc123", source),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "source_checkout_path",
                        return_value=checkout,
                    )
                )
                skill_manager.install_from_source(source, skill_names=["alpha"])
                foreign_source = root / "foreign"
                foreign_source.mkdir()
                (root / ".agents" / "skills" / "foreign").symlink_to(foreign_source)
                with self.assertRaises(skill_manager.SkillInstallError):
                    skill_manager.doctor()

    def test_remove_keeps_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            checkout = self._fixture_checkout(root)
            source = "https://github.com/Akira-TL/example.git"
            patches = self._patch_machine_paths(root)
            with ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "ensure_source_checkout",
                        return_value=(checkout, "abc123", source),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        skill_manager,
                        "source_checkout_path",
                        return_value=checkout,
                    )
                )
                skill_manager.install_from_source(source, skill_names=["alpha"])
                removed = skill_manager.remove_installed(["alpha"])

            self.assertEqual(removed, ["alpha"])
            self.assertFalse((root / ".agents" / "skills" / "alpha").exists())
            self.assertTrue(checkout.exists())

    def test_existing_non_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source"
            source.mkdir()
            target = root / "target"
            target.mkdir()
            with self.assertRaises(skill_manager.SkillInstallError):
                skill_manager.ensure_symlink(source, target)


class CliTests(unittest.TestCase):
    def test_install_defaults_to_machine_registry_without_scope_arguments(self) -> None:
        argv = [
            "skills.py",
            "install",
            "https://github.com/Akira-TL/example.git",
            "--skill",
            "alpha",
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(skills_cli, "install_from_source", return_value=["alpha"]) as install,
        ):
            self.assertEqual(skills_cli.main(), 0)

        install.assert_called_once_with(
            "https://github.com/Akira-TL/example.git",
            skill_names=["alpha"],
            install_all=False,
            include_roots=[],
            ref="main",
        )

    def test_cli_has_no_executor_or_project_scope_flags(self) -> None:
        help_text = skills_cli.build_parser().format_help()
        self.assertNotIn("--project", help_text)
        self.assertNotIn("enable", help_text)


if __name__ == "__main__":
    unittest.main()
