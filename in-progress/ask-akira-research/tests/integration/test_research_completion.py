from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database  # noqa: E402
from research_db_ops.completion import (  # noqa: E402
    literature_completion_readiness,
    validate_completion,
)


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

    def _insert_reviewed_candidate(
        self,
        candidate_id: int,
        paper_id: str,
        *,
        priority: str = "normal",
        depth: str = "full_scan",
    ) -> None:
        now = "2026-08-27T00:00:00+00:00"
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, status, read_depth, reading_status, critical_status,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', ?, 'extracted', 'critically_reviewed', ?, ?)
                """,
                (paper_id, f"Paper {paper_id}", depth, now, now),
            )
            connection.execute(
                """
                INSERT INTO candidates(
                    id, title, identity_status, relevance_status, paper_id,
                    created_at, updated_at, acquisition_status, reading_priority
                ) VALUES (?, ?, 'resolved', 'relevant', ?, ?, ?, 'acquired', ?)
                """,
                (candidate_id, f"Candidate {candidate_id}", paper_id, now, now, priority),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked, extraction_checks_json
                ) VALUES (?, 'reconstruction', ?, ?, ?, '[]', '[\"Methods > design\"]',
                          '{\"observation_semantics_checked\": true}')
                """,
                (paper_id, depth, now, now),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked
                ) VALUES (?, 'critical_audit', ?, ?, ?, '[]', '[\"Discussion > limitations\"]')
                """,
                (paper_id, depth, now, now),
            )

    def test_literature_completion_requires_core_deep_extraction(self) -> None:
        self._insert_reviewed_candidate(1, "P000001", priority="core", depth="full_scan")

        first = literature_completion_readiness(self.root, {"relevant_candidate_count": 1})
        reasons = {item["reason"] for item in first["blockers"]}
        self.assertIn("core_acquired_not_deep_extraction", reasons)

        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                "UPDATE papers SET read_depth = 'deep_extraction' WHERE id = 'P000001'"
            )
            connection.execute(
                "UPDATE reading_runs SET depth = 'deep_extraction' WHERE paper_id = 'P000001'"
            )
        second = literature_completion_readiness(self.root, {"relevant_candidate_count": 1})
        self.assertTrue(second["ready"])

    def test_literature_completion_requires_cross_paper_scientific_relation(self) -> None:
        self._insert_reviewed_candidate(1, "P000001")
        self._insert_reviewed_candidate(2, "P000002")
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                "INSERT INTO claims(paper_id, statement, claim_type) VALUES ('P000001', 'Claim A', 'descriptive')"
            )
            connection.execute(
                "INSERT INTO claims(paper_id, statement, claim_type) VALUES ('P000002', 'Claim B', 'descriptive')"
            )
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id, note, created_at
                ) VALUES ('paper', 'P000001', 'SHARES_DATA_WITH', 'paper', 'P000002',
                          'Shared dataset.', '2026-08-27T00:00:00+00:00')
                """
            )

        discovery = {
            "relevant_candidate_count": 2,
            "discovery_families": ["query_search", "citation_chasing"],
        }
        first = literature_completion_readiness(self.root, discovery)
        self.assertFalse(first["ready"])
        self.assertTrue(
            any(
                item["reason"] == "cross_paper_scientific_relation_missing"
                for item in first["blockers"]
            )
        )

        with sqlite3.connect(database_path(self.root)) as connection:
            claim_ids = [row[0] for row in connection.execute("SELECT id FROM claims ORDER BY id")]
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id, note, created_at
                ) VALUES ('claim', ?, 'QUALIFIES', 'claim', ?,
                          'Paper 2 narrows the scope of Paper 1.', '2026-08-27T00:00:00+00:00')
                """,
                (str(claim_ids[1]), str(claim_ids[0])),
            )
        second = literature_completion_readiness(self.root, discovery)
        self.assertTrue(second["ready"])
        self.assertEqual(second["cross_paper_scientific_relation_count"], 1)

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
