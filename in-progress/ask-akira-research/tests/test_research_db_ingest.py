from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database  # noqa: E402
from research_db_ingest import ingest_paper  # noqa: E402


class ResearchDbIngestPaperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        self.incoming = self.root / "incoming"
        self.incoming.mkdir()
        self.pdf_path = self.incoming / "source-paper.pdf"
        self.pdf_bytes = b"%PDF-1.4\nreal-enough-test-pdf\n"
        self.pdf_path.write_bytes(self.pdf_bytes)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def bundle(self, *, doi: str = "https://doi.org/10.1234/Test.Paper") -> dict:
        return {
            "title": "Test Paper",
            "doi": doi,
            "pmid": "12345678",
            "authors": ["A. Author", "B. Author"],
            "journal": "Test Journal",
            "year": 2026,
            "paper_type": "original_research",
            "artifacts": [
                {
                    "kind": "main_text",
                    "path": str(self.pdf_path),
                    "content_type": "application/pdf",
                    "version": "version-of-record",
                    "source": "publisher",
                    "source_url": "https://example.test/paper.pdf",
                }
            ],
        }

    def test_ingest_paper_copies_artifact_into_canonical_paper_directory(self) -> None:
        result = ingest_paper(self.root, self.bundle())

        self.assertEqual(result["paper_id"], "P000001")
        self.assertEqual(result["doi"], "10.1234/test.paper")
        self.assertEqual(result["paper_dir"], "literature/papers/P000001")
        self.assertNotIn("sha256", result["artifacts"][0])

        canonical_pdf = self.root / "literature" / "papers" / "P000001" / "paper.pdf"
        self.assertEqual(canonical_pdf.read_bytes(), self.pdf_bytes)
        self.assertTrue(self.pdf_path.exists(), "ingest should copy, not move, the source artifact")

        with sqlite3.connect(database_path(self.root)) as connection:
            paper = connection.execute(
                "SELECT id, doi, canonical_identity, status FROM papers"
            ).fetchone()
            artifact = connection.execute(
                "SELECT paper_id, path, content_type, source, source_url, retrieved_at FROM artifacts"
            ).fetchone()
            log_count = connection.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]

        self.assertEqual(
            paper,
            ("P000001", "10.1234/test.paper", "doi:10.1234/test.paper", "acquired"),
        )
        self.assertEqual(artifact[0], "P000001")
        self.assertEqual(artifact[1], "literature/papers/P000001/paper.pdf")
        self.assertEqual(artifact[2], "application/pdf")
        self.assertEqual(artifact[3], "publisher")
        self.assertEqual(artifact[4], "https://example.test/paper.pdf")
        self.assertIsNotNone(artifact[5])
        self.assertEqual(log_count, 2)

    def test_multiple_artifacts_receive_stable_names(self) -> None:
        supplement = self.incoming / "source-supplement.xlsx"
        supplement.write_bytes(b"xlsx placeholder")
        bundle = self.bundle()
        bundle["artifacts"].append(
            {
                "kind": "supplementary_tables",
                "path": str(supplement),
                "source": "publisher",
                "source_url": "https://example.test/supplement.xlsx",
            }
        )

        result = ingest_paper(self.root, bundle)

        paths = [artifact["path"] for artifact in result["artifacts"]]
        self.assertEqual(
            paths,
            [
                "literature/papers/P000001/paper.pdf",
                "literature/papers/P000001/supplementary-tables.xlsx",
            ],
        )

    def test_ingest_paper_allocates_monotonic_paper_ids(self) -> None:
        first = ingest_paper(self.root, self.bundle())
        second_pdf = self.incoming / "second.pdf"
        second_pdf.write_bytes(b"%PDF second")
        second = self.bundle(doi="10.1234/second")
        second["pmid"] = "87654321"
        second["title"] = "Second Paper"
        second["artifacts"][0]["path"] = str(second_pdf)

        second_result = ingest_paper(self.root, second)

        self.assertEqual(first["paper_id"], "P000001")
        self.assertEqual(second_result["paper_id"], "P000002")
        self.assertTrue((self.root / "literature/papers/P000002/paper.pdf").exists())

    def test_duplicate_doi_is_rejected_without_partial_write_or_directory(self) -> None:
        ingest_paper(self.root, self.bundle())
        duplicate = self.bundle(doi="DOI:10.1234/TEST.PAPER")
        duplicate["pmid"] = "99999999"

        with self.assertRaisesRegex(RuntimeError, "论文身份已存在"):
            ingest_paper(self.root, duplicate)

        with sqlite3.connect(database_path(self.root)) as connection:
            paper_count = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            log_count = connection.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]
        self.assertEqual((paper_count, artifact_count, log_count), (1, 1, 2))
        self.assertFalse((self.root / "literature/papers/P000002").exists())

    def test_missing_artifact_is_rejected_before_database_write(self) -> None:
        bundle = self.bundle()
        bundle["artifacts"] = [{"kind": "main_text", "path": "missing-paper.pdf"}]

        with self.assertRaisesRegex(RuntimeError, "文件不存在"):
            ingest_paper(self.root, bundle)

        with sqlite3.connect(database_path(self.root)) as connection:
            paper_count = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        self.assertEqual((paper_count, artifact_count), (0, 0))
        self.assertFalse((self.root / "literature/papers/P000001").exists())

    def test_identity_is_required_when_doi_and_pmid_are_absent(self) -> None:
        bundle = self.bundle()
        bundle.pop("doi")
        bundle.pop("pmid")

        with self.assertRaisesRegex(RuntimeError, "稳定论文身份"):
            ingest_paper(self.root, bundle)


if __name__ == "__main__":
    unittest.main()
