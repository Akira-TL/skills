from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, database_path, init_database  # noqa: E402
from research_db_ingest import ingest_paper  # noqa: E402


class ResearchDbIngestPaperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        self.paper_dir = self.root / "literature" / "papers" / "incoming"
        self.paper_dir.mkdir(parents=True)
        self.pdf_path = self.paper_dir / "paper.pdf"
        self.pdf_bytes = b"%PDF-1.4\nresearch smoke paper\n%%EOF\n"
        self.pdf_path.write_bytes(self.pdf_bytes)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _bundle(self, doi: str = "10.1234/Test.DOI") -> dict[str, object]:
        return {
            "title": "A Test Research Paper",
            "doi": doi,
            "authors": ["Akira Test", "Research Example"],
            "journal": "Journal of Smoke Tests",
            "year": 2026,
            "paper_type": "article",
            "artifacts": [
                {
                    "kind": "main_text",
                    "path": str(self.pdf_path.relative_to(self.root)),
                    "source": "publisher",
                    "source_url": "https://example.test/paper",
                    "version": "version_of_record",
                }
            ],
            "reason": "End-to-end ingest test",
        }

    def test_ingest_paper_registers_identity_artifact_and_change_log(self) -> None:
        result = ingest_paper(self.root, self._bundle())

        self.assertEqual(result["paper_id"], "P000001")
        self.assertEqual(result["doi"], "10.1234/test.doi")
        self.assertEqual(result["canonical_identity"], "doi:10.1234/test.doi")
        self.assertEqual(result["status"], "acquired")
        self.assertEqual(
            result["artifacts"][0]["sha256"], hashlib.sha256(self.pdf_bytes).hexdigest()
        )

        with sqlite3.connect(database_path(self.root)) as connection:
            paper = connection.execute(
                "SELECT id, status, doi, canonical_identity FROM papers"
            ).fetchone()
            artifact = connection.execute(
                "SELECT paper_id, path, sha256, content_type FROM artifacts"
            ).fetchone()
            log_count = connection.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]

        self.assertEqual(paper, ("P000001", "acquired", "10.1234/test.doi", "doi:10.1234/test.doi"))
        self.assertEqual(artifact[0], "P000001")
        self.assertEqual(artifact[1], str(self.pdf_path.relative_to(self.root)))
        self.assertEqual(artifact[2], hashlib.sha256(self.pdf_bytes).hexdigest())
        self.assertEqual(artifact[3], "application/pdf")
        self.assertEqual(log_count, 2)

    def test_ingest_paper_allocates_monotonic_paper_ids(self) -> None:
        first = ingest_paper(self.root, self._bundle("10.1234/first"))
        second_bundle = self._bundle("10.1234/second")
        second_bundle["title"] = "Second Test Paper"
        second = ingest_paper(self.root, second_bundle)

        self.assertEqual(first["paper_id"], "P000001")
        self.assertEqual(second["paper_id"], "P000002")

    def test_duplicate_doi_is_rejected_without_partial_write(self) -> None:
        ingest_paper(self.root, self._bundle("https://doi.org/10.1234/DUPLICATE"))

        with self.assertRaisesRegex(ResearchDbError, "论文身份已存在：P000001"):
            ingest_paper(self.root, self._bundle("doi:10.1234/duplicate"))

        with sqlite3.connect(database_path(self.root)) as connection:
            paper_count = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            log_count = connection.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]

        self.assertEqual((paper_count, artifact_count, log_count), (1, 1, 2))

    def test_missing_artifact_is_rejected_before_database_write(self) -> None:
        bundle = self._bundle()
        bundle["artifacts"] = [{"kind": "main_text", "path": "missing-paper.pdf"}]

        with self.assertRaisesRegex(ResearchDbError, "文件不存在"):
            ingest_paper(self.root, bundle)

        with sqlite3.connect(database_path(self.root)) as connection:
            paper_count = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

        self.assertEqual((paper_count, artifact_count), (0, 0))

    def test_identity_is_required_when_doi_and_pmid_are_absent(self) -> None:
        bundle = self._bundle()
        bundle.pop("doi")

        with self.assertRaisesRegex(ResearchDbError, "无法建立稳定论文身份"):
            ingest_paper(self.root, bundle)


if __name__ == "__main__":
    unittest.main()
