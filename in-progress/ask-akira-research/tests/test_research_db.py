from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database, status, validate  # noqa: E402


class ResearchDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_init_creates_v1_schema(self) -> None:
        result = init_database(self.root)

        self.assertEqual(result["schema_version"], 1)
        db_status = status(self.root)
        self.assertTrue(db_status["exists"])
        self.assertEqual(db_status["schema_version"], 1)
        self.assertEqual(db_status["meta_schema_version"], 1)
        self.assertEqual(db_status["tables"]["papers"], 0)
        self.assertTrue(validate(self.root)["ok"])

    def test_validate_requires_reconstruction_run_for_reconstructed_paper(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, status, read_depth, reading_status, critical_status,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', 'full_scan', 'reconstructed', 'not_reviewed', ?, ?)
                """,
                ("P000001", "Test Paper", now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("reconstruction run" in error for error in result["errors"]))

    def test_validate_detects_artifact_hash_mismatch(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        paper_dir = self.root / "literature" / "papers" / "P000001"
        paper_dir.mkdir(parents=True)
        pdf_path = paper_dir / "paper.pdf"
        pdf_path.write_bytes(b"not really a pdf")

        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO papers(id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("P000001", "Test Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    paper_id, kind, path, sha256, content_type, created_at
                ) VALUES (?, 'main_text', ?, ?, 'application/pdf', ?)
                """,
                (
                    "P000001",
                    str(pdf_path.relative_to(self.root)),
                    hashlib.sha256(b"different").hexdigest(),
                    now,
                ),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("SHA256" in error for error in result["errors"]))

    def test_validate_warns_when_critical_review_has_no_issue(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, status, read_depth, reading_status, critical_status,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', 'full_scan', 'reconstructed', 'critically_reviewed', ?, ?)
                """,
                ("P000001", "Test Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked
                ) VALUES (?, 'reconstruction', 'full_scan', ?, ?, '[]', '[]')
                """,
                ("P000001", now, now),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked
                ) VALUES (?, 'critical_audit', 'full_scan', ?, ?, '[]', '[]')
                """,
                ("P000001", now, now),
            )

        result = validate(self.root)
        self.assertTrue(result["ok"])
        self.assertTrue(any("没有记录 Issue" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
