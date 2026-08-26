from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import init_database  # noqa: E402
from research_db_ops.completion import validate_completion  # noqa: E402


class ResearchCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "research@example.test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Research Test"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_completion_rejects_repository_without_commit(self) -> None:
        result = validate_completion(self.root)

        self.assertFalse(result["ok"])
        self.assertTrue(any("尚无任何 Git commit" in error for error in result["errors"]))
        self.assertTrue(any("尚未被 Git 跟踪" in error for error in result["errors"]))

    def test_completion_requires_committed_canonical_research_state(self) -> None:
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "add",
                "RESEARCH.md",
                ".research/research.sqlite",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "RESEARCH: bootstrap project"],
            check=True,
            capture_output=True,
        )

        clean = validate_completion(self.root)
        self.assertTrue(clean["ok"])
        self.assertIsNotNone(clean["git"]["head"])

        (self.root / "RESEARCH.md").write_text("# Research\n\nchanged\n", encoding="utf-8")
        dirty = validate_completion(self.root)
        self.assertFalse(dirty["ok"])
        self.assertTrue(any("未提交修改" in error for error in dirty["errors"]))


if __name__ == "__main__":
    unittest.main()
