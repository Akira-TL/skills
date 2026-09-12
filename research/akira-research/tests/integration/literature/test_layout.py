from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_ops.completion.literature import literature_human_view_readiness  # noqa: E402
from research_db_ops.user_reading import confirmation_control, user_notes_block  # noqa: E402


def note(title: str = "论文") -> str:
    return (
        f"# {title}\n\n"
        + confirmation_control("top")
        + "\n\n## 三句话总结\n\n内容。\n\n## 结论边界\n\n内容。\n\n## 我的笔记\n\n"
        + user_notes_block()
        + "\n\n"
        + confirmation_control("bottom")
        + "\n"
    )


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

    def test_human_papers_directory_accepts_markdown_and_pdf(self) -> None:
        papers = self.root / "literature" / "papers"
        collections = self.root / "literature" / "collections"
        papers.mkdir(parents=True)
        collections.mkdir()
        (papers / "Paper title - Wang - 2026.md").write_text(note("Paper title"), encoding="utf-8")
        (papers / "Paper title - Wang - 2026.pdf").write_bytes(b"%PDF")
        (collections / "核心方法.md").write_text("# 核心方法\n", encoding="utf-8")
        (self.root / "literature" / "README.md").write_text("# 文献\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertTrue(result["ready"], result["blockers"])
        self.assertEqual(result["blockers"], [])

    def test_machine_readable_artifact_in_human_area_is_rejected(self) -> None:
        papers = self.root / "literature" / "papers"
        papers.mkdir(parents=True)
        (papers / "paper.xml").write_text("<article/>", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_non_readable_file")
        self.assertEqual(result["blockers"][0]["path"], "literature/papers/paper.xml")

    def test_old_state_directories_are_rejected(self) -> None:
        ad_hoc = self.root / "literature" / "to-read"
        ad_hoc.mkdir(parents=True)
        (ad_hoc / "paper.md").write_text("# old state directory\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_unexpected_top_level")
        self.assertEqual(result["blockers"][0]["path"], "literature/to-read")

    def test_human_paper_note_requires_confirmation_controls(self) -> None:
        papers = self.root / "literature" / "papers"
        papers.mkdir(parents=True)
        (papers / "Paper title - Wang - 2026.md").write_text("# 缺确认框\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(
            result["blockers"][0]["reason"],
            "human_literature_confirmation_controls_missing",
        )

    def test_unregistered_nested_human_directory_is_rejected(self) -> None:
        nested = self.root / "literature" / "papers" / "topic"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# note\n", encoding="utf-8")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(
            result["blockers"][0]["reason"],
            "human_literature_unregistered_legacy_file",
        )

    def test_pdf_without_matching_markdown_note_is_rejected(self) -> None:
        papers = self.root / "literature" / "papers"
        papers.mkdir(parents=True)
        (papers / "Paper title - Wang - 2026.pdf").write_bytes(b"%PDF")

        result = literature_human_view_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "human_literature_pdf_without_note")


if __name__ == "__main__":
    unittest.main()
