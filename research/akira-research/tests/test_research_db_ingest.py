from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database  # noqa: E402
from research_db_ingest import add_paper_artifacts, ingest_paper  # noqa: E402


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

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
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

    def test_extensionless_main_text_uses_content_type_for_canonical_suffix(self) -> None:
        html_path = self.incoming / "PMC_HTML"
        html_bytes = b"<!doctype html><html><body>paper</body></html>"
        html_path.write_bytes(html_bytes)
        bundle = self.bundle()
        bundle["artifacts"][0]["path"] = str(html_path)
        bundle["artifacts"][0]["content_type"] = "text/html"

        result = ingest_paper(self.root, bundle)

        self.assertEqual(
            result["artifacts"][0]["path"],
            "literature/papers/P000001/paper.html",
        )
        canonical_html = self.root / "literature" / "papers" / "P000001" / "paper.html"
        self.assertEqual(canonical_html.read_bytes(), html_bytes)
        self.assertTrue(html_path.exists(), "ingest should copy, not move, the source artifact")

    def test_doi_takes_precedence_over_explicit_identity_label(self) -> None:
        bundle = self.bundle()
        bundle["canonical_identity"] = "doi"

        result = ingest_paper(self.root, bundle)

        self.assertEqual(result["canonical_identity"], "doi:10.1234/test.paper")
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            canonical = connection.execute(
                "SELECT canonical_identity FROM papers WHERE id = 'P000001'"
            ).fetchone()[0]
        self.assertEqual(canonical, "doi:10.1234/test.paper")

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

    def test_add_paper_artifacts_appends_to_existing_canonical_directory(self) -> None:
        ingest_paper(self.root, self.bundle())
        supplement = self.incoming / "late-supplement.xlsx"
        supplement.write_bytes(b"late xlsx placeholder")

        result = add_paper_artifacts(
            self.root,
            {
                "paper_id": "P000001",
                "artifacts": [
                    {
                        "kind": "supplementary_tables",
                        "path": str(supplement),
                        "source": "publisher",
                        "source_url": "https://example.test/late-supplement.xlsx",
                    }
                ],
                "reason": "Late supplement acquisition",
            },
        )

        self.assertEqual(result["paper_id"], "P000001")
        self.assertEqual(
            result["artifacts"][0]["path"],
            "literature/papers/P000001/supplementary-tables.xlsx",
        )
        canonical = self.root / result["artifacts"][0]["path"]
        self.assertEqual(canonical.read_bytes(), b"late xlsx placeholder")
        self.assertTrue(supplement.exists(), "append should copy, not move, the source artifact")

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            artifacts = connection.execute(
                "SELECT kind, path, source_url FROM artifacts WHERE paper_id = 'P000001' ORDER BY id"
            ).fetchall()
            log_count = connection.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(artifacts[-1][0], "supplementary_tables")
        self.assertEqual(artifacts[-1][1], result["artifacts"][0]["path"])
        self.assertEqual(artifacts[-1][2], "https://example.test/late-supplement.xlsx")
        self.assertEqual(log_count, 3)

    def test_add_paper_artifacts_uses_suffix_without_overwriting_existing_file(self) -> None:
        bundle = self.bundle()
        first = self.incoming / "first-supplement.xlsx"
        first.write_bytes(b"first")
        bundle["artifacts"].append(
            {"kind": "supplementary_tables", "path": str(first)}
        )
        ingest_paper(self.root, bundle)
        second = self.incoming / "second-supplement.xlsx"
        second.write_bytes(b"second")

        result = add_paper_artifacts(
            self.root,
            {
                "paper_id": "P000001",
                "artifacts": [{"kind": "supplementary_tables", "path": str(second)}],
            },
        )

        self.assertEqual(
            result["artifacts"][0]["path"],
            "literature/papers/P000001/supplementary-tables-02.xlsx",
        )
        paper_dir = self.root / "literature" / "papers" / "P000001"
        self.assertEqual((paper_dir / "supplementary-tables.xlsx").read_bytes(), b"first")
        self.assertEqual((paper_dir / "supplementary-tables-02.xlsx").read_bytes(), b"second")

    def test_add_paper_artifacts_rejects_unknown_paper_without_copying(self) -> None:
        ingest_paper(self.root, self.bundle())
        supplement = self.incoming / "orphan-supplement.pdf"
        supplement.write_bytes(b"orphan")

        with self.assertRaisesRegex(RuntimeError, "Paper 不存在"):
            add_paper_artifacts(
                self.root,
                {
                    "paper_id": "P999999",
                    "artifacts": [{"kind": "supplementary_material", "path": str(supplement)}],
                },
            )

        self.assertFalse((self.root / "literature/papers/P999999").exists())
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0], 1)

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

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
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

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
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
