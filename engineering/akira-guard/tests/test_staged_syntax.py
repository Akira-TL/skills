from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from staged_syntax import staged_syntax_errors


class GitFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Guard Test")
        self.git("config", "user.email", "guard-test@example.test")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "CHORE: (test) initialize fixture")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def write(self, relative: str, content: str) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class StagedSyntaxTests(GitFixture):
    def test_reports_invalid_python_from_index(self) -> None:
        self.write("example.py", "def broken(:\n    pass\n")
        self.git("add", "example.py")

        errors = staged_syntax_errors(self.repo)

        self.assertEqual(len(errors), 1)
        self.assertIn("example.py", errors[0])

    def test_uses_staged_version_not_worktree_version(self) -> None:
        self.write("example.py", "value = 1\n")
        self.git("add", "example.py")
        self.write("example.py", "value =\n")

        self.assertEqual(staged_syntax_errors(self.repo), [])

    def test_staged_error_remains_after_worktree_is_fixed(self) -> None:
        self.write("example.py", "value =\n")
        self.git("add", "example.py")
        self.write("example.py", "value = 1\n")

        errors = staged_syntax_errors(self.repo)

        self.assertEqual(len(errors), 1)
        self.assertIn("example.py", errors[0])

    def test_parses_json_and_toml(self) -> None:
        self.write("config.json", '{"enabled": true}\n')
        self.write("config.toml", 'name = "guard"\n')
        self.git("add", "config.json", "config.toml")
        self.assertEqual(staged_syntax_errors(self.repo), [])

        self.write("config.json", '{"enabled": }\n')
        self.git("add", "config.json")
        errors = staged_syntax_errors(self.repo)
        self.assertEqual(len(errors), 1)
        self.assertIn("config.json", errors[0])

    @unittest.skipUnless(shutil.which("bash"), "bash is not available")
    def test_checks_shell_syntax_when_bash_is_available(self) -> None:
        self.write("script.sh", "if true; then\n  echo ok\nfi\n")
        self.git("add", "script.sh")
        self.assertEqual(staged_syntax_errors(self.repo), [])

        self.write("script.sh", "if true; then\n  echo broken\n")
        self.git("add", "script.sh")
        errors = staged_syntax_errors(self.repo)
        self.assertEqual(len(errors), 1)
        self.assertIn("script.sh", errors[0])

    def test_guard_commit_rejects_invalid_staged_python(self) -> None:
        self.write("broken.py", "def broken(:\n    pass\n")
        self.git("add", "broken.py")
        before = self.git("rev-parse", "HEAD").stdout.strip()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "guard.py"),
                "commit",
                "-m",
                "TEST: (guard) reject invalid syntax fixture",
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

        after = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(after, before)
        self.assertIn("暂存语法检查失败", result.stdout)


if __name__ == "__main__":
    unittest.main()
