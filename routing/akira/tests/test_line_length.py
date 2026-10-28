from __future__ import annotations

import argparse
import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_staged_syntax import GitFixture, SCRIPTS_ROOT

from guard import (
    architecture_scan_tree,
    build_parser,
    configured_line_length,
    line_length_violations,
    staged_line_length_violations,
)


class LineLengthTests(GitFixture):
    def stage(self, relative: str, content: str) -> None:
        self.write(relative, content)
        self.git("add", "--", relative)

    def baseline(self, content: str) -> None:
        self.stage("example.py", content)
        self.git("commit", "-q", "-m", "TEST: (guard) record historical code")

    def guard(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_ROOT / "guard.py"), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def test_exact_limit_passes_and_next_character_reports_location(self) -> None:
        self.stage("example.py", "#" * 120 + "\n" + "#" * 121 + "\n")
        self.assertEqual(
            staged_line_length_violations(self.repo, 120),
            ["example.py:2: 单行 121 字符，超过 120 字符上限"],
        )

    def test_counts_unicode_characters_and_excludes_crlf(self) -> None:
        data = ("中" * 120 + "\r\n" + "中" * 121 + "\r\n").encode("utf-8-sig")
        self.assertEqual(
            line_length_violations(Path("unicode.py"), data, 120),
            ["unicode.py:2: 单行 121 字符，超过 120 字符上限"],
        )

    def test_invalid_encoding_is_reported(self) -> None:
        self.assertIn("UTF-8", line_length_violations(Path("bad.py"), b"\xff", 120)[0])

    def test_uses_index_when_worktree_contains_long_line(self) -> None:
        self.stage("example.py", "value = 1\n")
        self.write("example.py", "#" * 2000 + "\n")
        self.assertEqual(staged_line_length_violations(self.repo, 120), [])

    def test_rejects_index_even_when_worktree_is_fixed(self) -> None:
        self.stage("example.py", "#" * 2000 + "\n")
        self.write("example.py", "value = 1\n")
        self.assertIn("2000 字符", staged_line_length_violations(self.repo, 120)[0])

    def test_unchanged_historical_long_line_does_not_block(self) -> None:
        self.baseline("a = 1\n" + "#" * 2000 + "\nb = 1\n")
        self.git("config", "diff.interHunkContext", "10")
        self.stage("example.py", "a = 2\n" + "#" * 2000 + "\nb = 2\n")
        self.assertEqual(staged_line_length_violations(self.repo, 120), [])

    def test_modified_historical_long_line_is_checked(self) -> None:
        self.baseline("#" * 2000 + "\n")
        self.stage("example.py", "#" * 1500 + "\n")
        self.assertIn("1500 字符", staged_line_length_violations(self.repo, 120)[0])

    def test_deleted_long_line_does_not_block(self) -> None:
        self.baseline("#" * 2000 + "\nvalue = 1\n")
        self.stage("example.py", "value = 1\n")
        self.assertEqual(staged_line_length_violations(self.repo, 120), [])

    def test_deleted_file_does_not_block(self) -> None:
        self.baseline("#" * 2000 + "\n")
        self.git("rm", "example.py")
        self.assertEqual(staged_line_length_violations(self.repo, 120), [])

    def test_literal_path_and_missing_final_newline(self) -> None:
        self.stage("[1]* code.py", "#" * 121)
        self.assertEqual(
            staged_line_length_violations(self.repo, 120),
            ["[1]* code.py:1: 单行 121 字符，超过 120 字符上限"],
        )

    def test_binary_diff_attribute_cannot_hide_long_code(self) -> None:
        self.stage(".gitattributes", "*.py -diff\n")
        self.stage("example.py", "#" * 121 + "\n")
        self.assertEqual(len(staged_line_length_violations(self.repo, 120)), 1)

    def test_renamed_code_is_checked_at_new_path(self) -> None:
        self.baseline("#" * 121 + "\n")
        self.git("mv", "example.py", "renamed.py")
        self.assertEqual(
            staged_line_length_violations(self.repo, 120),
            ["renamed.py:1: 单行 121 字符，超过 120 字符上限"],
        )

    def test_shell_and_frontend_extensions_are_checked(self) -> None:
        for suffix in (".sh", ".mjs", ".tsx", ".vue", ".css", ".html", ".sql"):
            self.stage(f"source{suffix}", "x" * 121 + "\n")
        self.assertEqual(len(staged_line_length_violations(self.repo, 120)), 7)

    def test_docs_and_ignored_directories_are_skipped(self) -> None:
        self.stage("article.md", "x" * 2000 + "\n")
        self.stage("vendor/example.py", "#" * 2000 + "\n")
        self.assertEqual(staged_line_length_violations(self.repo, 120), [])

    def test_tree_scan_reports_historical_long_lines(self) -> None:
        self.write("example.py", "#" * 121 + "\n")
        self.assertEqual(
            architecture_scan_tree(self.repo, 120),
            ["example.py:1: 单行 121 字符，超过 120 字符上限"],
        )

    def test_tree_scan_skips_nested_repositories(self) -> None:
        nested = self.repo / "child"
        nested.mkdir()
        subprocess.run(["git", "init", "-q", str(nested)], check=True, capture_output=True)
        (nested / "example.py").write_text("#" * 2000 + "\n", encoding="utf-8")
        self.assertEqual(architecture_scan_tree(self.repo, 120), [])

    def test_default_config_is_120(self) -> None:
        missing = subprocess.CompletedProcess([], 1, stdout="", stderr="")
        with patch("guard.run_git", return_value=missing):
            self.assertEqual(configured_line_length(self.repo), 120)

    def test_project_config_and_command_override(self) -> None:
        self.git("config", "akira.guardMaxLineLength", "160")
        self.assertEqual(configured_line_length(self.repo), 160)
        self.assertEqual(configured_line_length(self.repo, 100), 100)

    def test_invalid_git_config_fails(self) -> None:
        for value in ("0", "-1", "abc", "120.5", ""):
            with self.subTest(value=value):
                self.git("config", "akira.guardMaxLineLength", value)
                with self.assertRaises(ValueError):
                    configured_line_length(self.repo)

    def test_cli_rejects_nonpositive_limit(self) -> None:
        parser = build_parser()
        for value in ("0", "-1", "abc"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    parser.parse_args(["check", "--max-line-length", value])
                self.assertEqual(error.exception.code, 2)

    def test_commands_accept_limit_argument(self) -> None:
        for command in ("check", "architecture", "commit"):
            argv = [command, "--max-line-length", "100"]
            if command == "commit":
                argv.extend(["-m", "TEST: (guard) check parser"])
            args = build_parser().parse_args(argv)
            self.assertIsInstance(args, argparse.Namespace)
            self.assertEqual(args.max_line_length, 100)

    def test_commit_blocks_long_lines_even_with_architecture_override(self) -> None:
        self.stage("example.py", "#" * 121 + "\n")
        before = self.git("rev-parse", "HEAD").stdout
        result = self.guard(
            "commit", "-m", "TEST: (guard) block long line",
            "--max-line-length", "120", "--allow-architecture-warnings",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.assertIn("example.py:1", result.stdout)
        self.assertIn("暂存单行长度检查失败", result.stdout)

    def test_commit_accepts_exact_limit(self) -> None:
        self.stage("example.py", "#" * 120 + "\n")
        before = self.git("rev-parse", "HEAD").stdout
        result = self.guard(
            "commit", "-m", "TEST: (guard) accept exact length", "--max-line-length", "120"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.git("rev-parse", "HEAD").stdout, before)

    def test_cli_config_and_override_control_staged_check(self) -> None:
        self.stage("example.py", "#" * 121 + "\n")
        self.git("config", "akira.guardMaxLineLength", "120")
        self.assertEqual(self.guard("architecture", "--staged").returncode, 1)
        result = self.guard("architecture", "--staged", "--max-line-length", "160")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_config_returns_message_without_traceback(self) -> None:
        self.git("config", "akira.guardMaxLineLength", "bad")
        result = self.guard("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("akira.guardMaxLineLength", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
