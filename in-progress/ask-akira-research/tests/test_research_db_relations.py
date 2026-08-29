from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, database_path, init_database  # noqa: E402
from research_db_ops.query import paper_history, related_papers  # noqa: E402
from research_db_ops.relations import add_relation  # noqa: E402


class ResearchDbRelationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            for paper_id, title, doi in (
                ("P000001", "Paper one", "10.1234/one"),
                ("P000002", "Paper two", "10.1234/two"),
            ):
                connection.execute(
                    """
                    INSERT INTO papers(
                        id, title, doi, canonical_identity, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (paper_id, title, doi, f"doi:{doi}", now, now),
                )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_add_cross_paper_relation_is_visible_from_both_papers(self) -> None:
        result = add_relation(
            self.root,
            {
                "subject_type": "paper",
                "subject_id": "P000001",
                "predicate": "SHARES_DATA_WITH",
                "object_type": "paper",
                "object_id": "P000002",
                "confidence": "high",
                "note": "Both papers report the same accession and cohort.",
            },
        )

        self.assertEqual(result["paper_ids"], ["P000001", "P000002"])
        related_one = related_papers(self.root, "P000001")
        related_two = related_papers(self.root, "P000002")
        self.assertEqual(related_one["related"][0]["paper"]["id"], "P000002")
        self.assertEqual(related_two["related"][0]["paper"]["id"], "P000001")
        self.assertEqual(len(paper_history(self.root, "P000001")["history"]), 1)
        self.assertEqual(len(paper_history(self.root, "P000002")["history"]), 1)

    def test_relation_requires_explicit_note(self) -> None:
        with self.assertRaises(ResearchDbError):
            add_relation(
                self.root,
                {
                    "subject_type": "paper",
                    "subject_id": "P000001",
                    "predicate": "CITES",
                    "object_type": "paper",
                    "object_id": "P000002",
                },
            )

    def test_relation_rejects_ambiguous_supports(self) -> None:
        with self.assertRaises(ResearchDbError):
            add_relation(
                self.root,
                {
                    "subject_type": "paper",
                    "subject_id": "P000001",
                    "predicate": "SUPPORTS",
                    "object_type": "paper",
                    "object_id": "P000002",
                    "note": "Ambiguous support relation.",
                },
            )

    def test_duplicate_relation_is_rejected(self) -> None:
        bundle = {
            "subject_type": "paper",
            "subject_id": "P000001",
            "predicate": "SHARES_SAMPLES_WITH",
            "object_type": "paper",
            "object_id": "P000002",
            "note": "Same participant samples are reused.",
        }
        add_relation(self.root, bundle)
        with self.assertRaises(ResearchDbError):
            add_relation(self.root, bundle)


if __name__ == "__main__":
    unittest.main()
