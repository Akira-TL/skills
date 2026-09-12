from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "zotero_export.py"
SPEC = importlib.util.spec_from_file_location("zotero_export", SCRIPT)
assert SPEC and SPEC.loader
zotero_export = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = zotero_export
SPEC.loader.exec_module(zotero_export)


class ZoteroExportTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        db_dir = root / ".research"
        db_dir.mkdir()
        connection = sqlite3.connect(db_dir / "research.sqlite")
        connection.executescript(
            """
            CREATE TABLE papers (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, doi TEXT, pmid TEXT,
                authors TEXT, journal TEXT, year INTEGER, paper_type TEXT
            );
            CREATE TABLE candidates (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, doi TEXT, pmid TEXT,
                authors TEXT, year INTEGER, paper_id TEXT, relevance_status TEXT,
                reading_priority TEXT, source_url TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "P000001",
                "Core paper",
                "10.1000/core",
                "12345",
                json.dumps(["Alice Example", "Bob Example"]),
                "Journal X",
                2025,
                "original research",
            ),
        )
        connection.executemany(
            "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Core paper", "10.1000/core", "12345", None, 2025, "P000001", "relevant", "core", "https://example.test/core"),
                (2, "High paper", "10.1000/high", None, json.dumps(["Carol Example"]), 2024, None, "relevant", "high", "https://example.test/high"),
                (3, "Normal paper", "10.1000/normal", None, None, 2023, None, "relevant", "normal", None),
                (4, "Excluded core", "10.1000/excluded", None, None, 2022, None, "excluded", "core", None),
            ],
        )
        connection.commit()
        connection.close()
        return root

    def test_default_selection_is_core_and_high_relevant_only(self) -> None:
        root = self.make_project()
        papers = zotero_export.load_recommendations(
            root / ".research" / "research.sqlite", ("core", "high")
        )
        self.assertEqual([paper.title for paper in papers], ["Core paper", "High paper"])
        self.assertEqual(papers[0].journal, "Journal X")
        self.assertEqual(papers[0].authors, ("Alice Example", "Bob Example"))

    def test_ris_contains_stable_identity_without_inventing_missing_fields(self) -> None:
        root = self.make_project()
        papers = zotero_export.load_recommendations(
            root / ".research" / "research.sqlite", ("core",)
        )
        output = root / "out.ris"
        zotero_export.write_ris(papers, output)
        text = output.read_text(encoding="utf-8")
        self.assertIn("TI  - Core paper", text)
        self.assertIn("DO  - 10.1000/core", text)
        self.assertIn("AN  - PMID:12345", text)
        self.assertIn("AU  - Alice Example", text)

    def test_existing_doi_is_added_to_collection_without_recreating_item(self) -> None:
        paper = zotero_export.Paper(
            candidate_id=1,
            priority="core",
            title="Core paper",
            doi="10.1000/core",
            pmid=None,
            authors=(),
            year=2025,
            journal=None,
            paper_type=None,
            source_url=None,
        )
        items = [
            {
                "data": {
                    "key": "ABC12345",
                    "version": 7,
                    "itemType": "journalArticle",
                    "title": "Core paper",
                    "date": "2025",
                    "DOI": "https://doi.org/10.1000/CORE",
                    "collections": ["OLD11111"],
                }
            }
        ]
        changes, new_count, existing_count = zotero_export.build_item_changes(
            [paper], "TARGET01", items
        )
        self.assertEqual(new_count, 0)
        self.assertEqual(existing_count, 1)
        self.assertEqual(changes[0]["key"], "ABC12345")
        self.assertEqual(changes[0]["collections"], ["OLD11111", "TARGET01"])

    def test_title_fallback_requires_year(self) -> None:
        paper = zotero_export.Paper(
            candidate_id=5,
            priority="high",
            title="Same title",
            doi=None,
            pmid=None,
            authors=(),
            year=None,
            journal=None,
            paper_type=None,
            source_url=None,
        )
        items = [{"data": {"key": "OLD00001", "version": 1, "itemType": "journalArticle", "title": "Same title", "date": "", "collections": []}}]
        changes, new_count, existing_count = zotero_export.build_item_changes([paper], "TARGET01", items)
        self.assertEqual(new_count, 1)
        self.assertEqual(existing_count, 0)
        self.assertNotIn("key", changes[0])

    def test_file_only_cli_never_requires_zotero(self) -> None:
        root = self.make_project()
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = zotero_export.main(["--project-root", str(root), "--file-only"])
        self.assertEqual(status, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["status"], "fallback_only")
        self.assertEqual(result["selected"], 2)
        self.assertTrue(Path(result["ris"]).is_file())


if __name__ == "__main__":
    unittest.main()
