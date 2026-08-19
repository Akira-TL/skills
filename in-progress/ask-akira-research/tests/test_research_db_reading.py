from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database, validate  # noqa: E402
from research_db_critical import ingest_critical  # noqa: E402
from research_db_ingest import ingest_paper  # noqa: E402
from research_db_reading import ingest_reading  # noqa: E402


class ResearchDbReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        incoming = self.root / "incoming"
        incoming.mkdir()
        pdf = incoming / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\nreading-test\n")
        ingest_paper(
            self.root,
            {
                "title": "Reading Test Paper",
                "doi": "10.1234/reading-test",
                "artifacts": [
                    {
                        "kind": "main_text",
                        "path": str(pdf),
                        "source": "publisher",
                        "source_url": "https://example.test/reading.pdf",
                    }
                ],
            },
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def reconstruction_bundle(self) -> dict:
        return {
            "paper_id": "P000001",
            "depth": "full_scan",
            "artifacts_checked": [{"artifact_kind": "main_text"}],
            "sections_checked": ["Introduction", "Methods", "Results", "Discussion"],
            "methods": [
                {
                    "ref": "method-1",
                    "name": "Stool DNA extraction",
                    "purpose": "Extract microbial DNA",
                    "description": "200 mg stool processed with a commercial kit.",
                    "parameters": {"input_mass_mg": 200},
                    "artifact_kind": "main_text",
                    "source_locator": "Methods > DNA extraction",
                }
            ],
            "experiments": [
                {
                    "ref": "experiment-1",
                    "question": "Does altitude exposure alter the gut microbiome?",
                    "design": "longitudinal repeated measures",
                    "samples": "45 participants over multiple time points",
                    "artifact_kind": "main_text",
                    "source_locator": "Methods > Study design",
                }
            ],
            "observations": [
                {
                    "ref": "observation-1",
                    "experiment_ref": "experiment-1",
                    "statement": "Blautia abundance increased during altitude exposure.",
                    "effect": "increase",
                    "certainty": "reported",
                    "artifact_kind": "main_text",
                    "source_locator": "Results > longitudinal microbiome changes",
                }
            ],
            "claims": [
                {
                    "ref": "claim-1",
                    "statement": "Blautia may contribute to hypoxia acclimatization.",
                    "claim_type": "causal",
                    "author_strength": "suggestive",
                    "artifact_kind": "main_text",
                    "source_locator": "Discussion",
                }
            ],
            "leads": [
                {
                    "ref": "lead-1",
                    "type": "dataset",
                    "title": "Metagenomic sequencing data",
                    "identifier": "BioProject-test",
                    "purpose": "Potential reanalysis",
                    "artifact_kind": "main_text",
                    "source_locator": "Data availability",
                }
            ],
            "relations": [
                {
                    "subject_type": "experiment",
                    "subject_ref": "experiment-1",
                    "predicate": "USES",
                    "object_type": "method",
                    "object_ref": "method-1",
                },
                {
                    "subject_type": "observation",
                    "subject_ref": "observation-1",
                    "predicate": "SUPPORTS",
                    "object_type": "claim",
                    "object_ref": "claim-1",
                },
            ],
        }

    def test_reconstruction_bundle_is_atomic_and_updates_paper_state(self) -> None:
        result = ingest_reading(self.root, self.reconstruction_bundle())

        self.assertEqual(result["reading_status"], "reconstructed")
        self.assertEqual(result["counts"]["methods"], 1)
        self.assertEqual(result["counts"]["relations"], 2)
        self.assertIn("claim:claim-1", result["refs"])

        with sqlite3.connect(database_path(self.root)) as connection:
            paper = connection.execute(
                "SELECT status, read_depth, reading_status, critical_status FROM papers"
            ).fetchone()
            counts = tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("methods", "experiments", "observations", "claims", "leads", "relations", "reading_runs")
            )
        self.assertEqual(paper, ("active", "full_scan", "reconstructed", "not_reviewed"))
        self.assertEqual(counts, (1, 1, 1, 1, 1, 2, 1))
        self.assertTrue(validate(self.root)["ok"])

    def test_bad_relation_rolls_back_entire_reconstruction(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["relations"].append(
            {
                "subject_type": "observation",
                "subject_ref": "missing-observation",
                "predicate": "SUPPORTS",
                "object_type": "claim",
                "object_ref": "claim-1",
            }
        )

        with self.assertRaisesRegex(RuntimeError, "未知 bundle ref"):
            ingest_reading(self.root, bundle)

        with sqlite3.connect(database_path(self.root)) as connection:
            counts = tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("methods", "experiments", "observations", "claims", "leads", "relations", "reading_runs")
            )
            paper = connection.execute(
                "SELECT reading_status FROM papers WHERE id='P000001'"
            ).fetchone()[0]
        self.assertEqual(counts, (0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(paper, "unread")

    def test_critical_audit_requires_reconstruction(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "尚未完成 Reconstruction"):
            ingest_critical(
                self.root,
                {
                    "paper_id": "P000001",
                    "artifacts_checked": [{"artifact_kind": "main_text"}],
                    "sections_checked": ["Methods", "Discussion"],
                    "issues": [],
                },
            )

    def test_critical_audit_links_issue_and_sidecar(self) -> None:
        reading = ingest_reading(self.root, self.reconstruction_bundle())
        claim_id = reading["refs"]["claim:claim-1"]
        sidecar = self.root / "literature" / "papers" / "P000001" / "README.md"
        sidecar.write_text("# Reading Test Paper\n\nCritical synthesis.\n", encoding="utf-8")

        result = ingest_critical(
            self.root,
            {
                "paper_id": "P000001",
                "depth": "deep_extraction",
                "artifacts_checked": [{"artifact_kind": "main_text"}],
                "sections_checked": ["Methods", "Results", "Discussion"],
                "sidecar_path": "literature/papers/P000001/README.md",
                "issues": [
                    {
                        "ref": "issue-1",
                        "category": "population_scope",
                        "nature": "scope_limitation",
                        "target_type": "claim",
                        "target_id": claim_id,
                        "assessment": "The cohort does not establish generalizability beyond the sampled population.",
                        "basis": "demonstrated",
                        "severity": "moderate",
                        "confidence": "high",
                        "why_it_matters": "The causal claim should retain a population scope.",
                        "artifact_kind": "main_text",
                        "source_locator": "Methods > Participants",
                    }
                ],
                "relations": [
                    {
                        "subject_type": "issue",
                        "subject_ref": "issue-1",
                        "predicate": "LIMITS",
                        "object_type": "claim",
                        "object_id": claim_id,
                    }
                ],
            },
        )

        self.assertEqual(result["critical_status"], "critically_reviewed")
        self.assertEqual(result["reading_status"], "extracted")
        self.assertEqual(result["counts"], {"issues": 1, "relations": 1})
        self.assertEqual(result["sidecar_path"], "literature/papers/P000001/README.md")

        with sqlite3.connect(database_path(self.root)) as connection:
            paper = connection.execute(
                "SELECT read_depth, reading_status, critical_status, sidecar_path FROM papers"
            ).fetchone()
            issue = connection.execute(
                "SELECT nature, basis, target_type, target_id FROM issues"
            ).fetchone()
            passes = connection.execute(
                "SELECT pass FROM reading_runs ORDER BY id"
            ).fetchall()
        self.assertEqual(
            paper,
            (
                "deep_extraction",
                "extracted",
                "critically_reviewed",
                "literature/papers/P000001/README.md",
            ),
        )
        self.assertEqual(issue, ("scope_limitation", "demonstrated", "claim", claim_id))
        self.assertEqual(passes, [("reconstruction",), ("critical_audit",)])
        self.assertTrue(validate(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
