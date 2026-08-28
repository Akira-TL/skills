from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import (  # noqa: E402
    MIGRATION_DIR,
    apply_migrations,
    database_path,
    init_database,
    status,
    validate,
)


class ResearchDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_init_creates_current_schema(self) -> None:
        result = init_database(self.root)

        self.assertEqual(result["schema_version"], 15)
        self.assertEqual(
            Path(result["bundle_directory"]), self.root / ".research" / "bundles"
        )
        self.assertTrue((self.root / ".research" / "bundles").is_dir())
        db_status = status(self.root)
        self.assertTrue(db_status["exists"])
        self.assertEqual(db_status["schema_version"], 15)
        self.assertEqual(db_status["meta_schema_version"], 15)
        self.assertEqual(db_status["tables"]["papers"], 0)
        self.assertTrue(validate(self.root)["ok"])

        with sqlite3.connect(database_path(self.root)) as connection:
            artifact_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(artifacts)")
            }
            issue_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(issues)")
            }
        self.assertNotIn("sha256", artifact_columns)
        self.assertIn("nature", issue_columns)
        with sqlite3.connect(database_path(self.root)) as connection:
            fts_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'knowledge_fts'"
            ).fetchone()
        self.assertIsNotNone(fts_table)

    def test_migrate_v1_to_v2_preserves_artifacts_and_maps_issue_model(self) -> None:
        db_path = database_path(self.root)
        db_path.parent.mkdir(parents=True)
        v1_sql = (MIGRATION_DIR / "001_initial.sql").read_text(encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(db_path) as connection:
            connection.executescript(v1_sql)
            connection.execute("PRAGMA user_version = 1")
            connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', '1')"
            )
            connection.execute(
                "INSERT INTO papers(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("P000001", "Legacy Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO artifacts(paper_id, kind, path, sha256, created_at)
                VALUES (?, 'main_text', 'legacy.pdf', 'legacy-hash', ?)
                """,
                ("P000001", now),
            )
            connection.execute(
                """
                INSERT INTO issues(
                    paper_id, category, assessment, basis, severity, confidence, created_at
                ) VALUES (?, 'design', 'Legacy issue', 'potential_concern',
                          'major', 'medium', ?)
                """,
                ("P000001", now),
            )

        self.assertEqual(apply_migrations(db_path), [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            artifact_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(artifacts)")
            }
            artifact = connection.execute(
                "SELECT paper_id, kind, path FROM artifacts"
            ).fetchone()
            issue = connection.execute(
                "SELECT nature, basis, severity, confidence FROM issues"
            ).fetchone()

        self.assertNotIn("sha256", artifact_columns)
        self.assertEqual(tuple(artifact), ("P000001", "main_text", "legacy.pdf"))
        self.assertEqual(tuple(issue), ("concern", "potential", "major", "medium"))

    def test_candidate_link_is_backfilled_when_migrating_from_v4(self) -> None:
        db_path = database_path(self.root)
        db_path.parent.mkdir(parents=True)
        with sqlite3.connect(db_path) as connection:
            for migration_name in (
                "001_initial.sql",
                "002_provenance_and_issue_model.sql",
                "003_knowledge_fts.sql",
                "004_discovery_workflow.sql",
            ):
                connection.executescript((MIGRATION_DIR / migration_name).read_text(encoding="utf-8"))
            connection.execute("PRAGMA user_version = 4")
            connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', '4')"
            )
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, created_at, updated_at
                ) VALUES ('P000001', 'Known paper', '10.1234/known',
                          'doi:10.1234/known', ?, ?)
                """,
                (now, now),
            )
            connection.execute(
                """
                INSERT INTO candidates(
                    title, doi, identity_status, relevance_status, paper_id,
                    created_at, updated_at
                ) VALUES ('Known paper', '10.1234/known', 'resolved', 'relevant',
                          'P000001', ?, ?)
                """,
                (now, now),
            )

        self.assertEqual(apply_migrations(db_path), [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT acquisition_status, identity_status FROM candidates"
            ).fetchone()
        self.assertEqual(tuple(row), ("acquired", "resolved"))

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

    def test_validate_detects_missing_artifact_file(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO papers(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("P000001", "Test Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    paper_id, kind, path, content_type, retrieved_at, created_at
                ) VALUES (?, 'main_text', ?, 'application/pdf', ?, ?)
                """,
                ("P000001", "literature/papers/P000001/paper.pdf", now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("文件不存在" in error for error in result["errors"]))

    def test_validate_rejects_canonical_identity_that_conflicts_with_doi(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "P000001",
                    "Test Paper",
                    "10.1234/test.paper",
                    "doi",
                    now,
                    now,
                ),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("canonical_identity" in error for error in result["errors"]))

    def test_validate_rejects_extensionless_main_text_artifact(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        paper_dir = self.root / "literature" / "papers" / "P000001"
        paper_dir.mkdir(parents=True)
        (paper_dir / "paper").write_text("<html></html>", encoding="utf-8")
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO papers(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("P000001", "Test Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    paper_id, kind, path, content_type, retrieved_at, created_at
                ) VALUES (?, 'main_text', ?, 'text/html', ?, ?)
                """,
                ("P000001", "literature/papers/P000001/paper", now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("扩展名" in error for error in result["errors"]))

    def test_validate_rejects_excluded_candidate_without_reason(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO candidates(
                    title, identity_status, relevance_status, acquisition_status,
                    reading_priority, created_at, updated_at
                ) VALUES ('Noise result', 'unresolved', 'excluded', 'pending',
                          'low', ?, ?)
                """,
                (now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("exclusion_reason" in error for error in result["errors"]))

    def test_validate_rejects_duplicate_candidate_stable_identity(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            for title in ("Index title A", "Index title B"):
                connection.execute(
                    """
                    INSERT INTO candidates(
                        title, doi, identity_status, relevance_status,
                        acquisition_status, reading_priority, created_at, updated_at
                    ) VALUES (?, '10.1234/duplicate', 'resolved', 'relevant',
                              'queued', 'normal', ?, ?)
                    """,
                    (title, now, now),
                )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("重复稳定身份 DOI" in error for error in result["errors"]))

    def test_validate_rejects_acquired_candidate_without_paper(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO candidates(
                    title, doi, identity_status, relevance_status, acquisition_status,
                    reading_priority, created_at, updated_at
                ) VALUES ('Orphan acquired result', '10.1234/orphan', 'resolved',
                          'relevant', 'acquired', 'core', ?, ?)
                """,
                (now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("没有关联 Paper" in error for error in result["errors"]))

    def test_validate_rejects_candidate_paper_identity_conflict(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, created_at, updated_at
                ) VALUES ('P000001', 'Known paper', '10.1234/paper',
                          'doi:10.1234/paper', ?, ?)
                """,
                (now, now),
            )
            connection.execute(
                """
                INSERT INTO candidates(
                    title, doi, identity_status, relevance_status, acquisition_status,
                    reading_priority, paper_id, created_at, updated_at
                ) VALUES ('Wrong identity', '10.1234/other', 'resolved', 'relevant',
                          'acquired', 'core', 'P000001', ?, ?)
                """,
                (now, now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("DOI" in error and "不一致" in error for error in result["errors"]))

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
            for reading_pass in ("reconstruction", "critical_audit"):
                checks = '{"observation_semantics_checked": true}' if reading_pass == "reconstruction" else None
                connection.execute(
                    """
                    INSERT INTO reading_runs(
                        paper_id, pass, depth, started_at, completed_at,
                        artifacts_checked, sections_checked, extraction_checks_json
                    ) VALUES (?, ?, 'full_scan', ?, ?, '[]', '[]', ?)
                    """,
                    ("P000001", reading_pass, now, now, checks),
                )

        result = validate(self.root)
        self.assertTrue(result["ok"])
        self.assertTrue(any("没有记录 Issue" in warning for warning in result["warnings"]))

    def test_not_reported_issue_still_requires_locator(self) -> None:
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO papers(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("P000001", "Test Paper", now, now),
            )
            connection.execute(
                """
                INSERT INTO issues(
                    paper_id, category, nature, assessment, basis, severity,
                    confidence, created_at
                ) VALUES (?, 'reporting', 'reporting_gap', ?, 'not_reported',
                          'moderate', 'high', ?)
                """,
                ("P000001", "Randomization procedure is not reported.", now),
            )

        result = validate(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("not_reported" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
