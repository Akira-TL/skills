from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_ops.completion.literature import literature_human_view_readiness  # noqa: E402


class LiteratureHumanViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_missing_literature_directory_is_valid(self) -> None:
        result = literature_human_view_readiness(self.root)
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_human_reading_directories_accept_only_markdown_and_pdf(self) -> None:
        to_read = self.root / "literature" / "to-read"
        read = self.root / "literature" / "read"
        collections = self.root / "literature" / "collections"
        to_read.mkdir(parents=True)
        read.mkdir()
        collections.mkdir()
        (to_read / "Paper title - Wang - 2026.md").write_text("# 待读\n", encoding="utf-8")
        (to_read / "Paper title - Wang - 2026.pdf").write_bytes(b"%PDF")
        (read / "Other paper - Li - 2025.md").write_text("# 已读\n", encoding="utf-8")
        (collections / "核心方法.md").write_text("# 核心方法\n", encoding="utf-8")
        (self.root / "literature" / "README.md").write_text("# 文献\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_machine_readable_artifact_in_human_area_is_rejected(self) -> None:
        read = self.root / "literature" / "read"
        read.mkdir(parents=True)
        (read / "paper.xml").write_text("<article/>", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_non_readable_file")
        self.assertEqual(result["blockers"][0]["path"], "literature/read/paper.xml")

    def test_ad_hoc_topic_directory_is_rejected(self) -> None:
        ad_hoc = self.root / "literature" / "Dprime_must_read"
        ad_hoc.mkdir(parents=True)
        (ad_hoc / "paper.pdf").write_bytes(b"%PDF")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_unexpected_top_level")
        self.assertEqual(result["blockers"][0]["path"], "literature/Dprime_must_read")

    def test_reading_area_must_be_flat(self) -> None:
        nested = self.root / "literature" / "read" / "P000001"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# note\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_nested_directory")

    def test_pdf_without_matching_markdown_note_is_rejected(self) -> None:
        to_read = self.root / "literature" / "to-read"
        to_read.mkdir(parents=True)
        (to_read / "Paper title - Wang - 2026.pdf").write_bytes(b"%PDF")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_pdf_without_note")


if __name__ == "__main__":
    unittest.main()
