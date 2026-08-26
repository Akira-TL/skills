from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database  # noqa: E402
from research_db_ops.query import (  # noqa: E402
    evidence_packet,
    get_paper,
    list_entities,
    paper_history,
    related_papers,
    search_knowledge,
)


class ResearchDbQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        now = datetime.now(timezone.utc).isoformat()
        artifact_path = self.root / "paper.html"
        artifact_path.write_text("paper", encoding="utf-8")
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, status, read_depth,
                    reading_status, critical_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'active', 'deep_extraction', 'extracted',
                          'critically_reviewed', ?, ?)
                """,
                (
                    "P000001",
                    "Altitude gut microbiome study",
                    "10.1234/altitude",
                    "doi:10.1234/altitude",
                    now,
                    now,
                ),
            )
            artifact_id = connection.execute(
                """
                INSERT INTO artifacts(
                    paper_id, kind, path, content_type, retrieved_at, created_at
                ) VALUES (?, 'main_text', ?, 'text/html', ?, ?)
                """,
                ("P000001", str(artifact_path), now, now),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO methods(
                    paper_id, name, purpose, description, artifact_id, source_locator
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "P000001",
                    "Shotgun metagenomics",
                    "Profile microbial genomes",
                    "Whole-genome shotgun sequencing and genome-resolved profiling.",
                    artifact_id,
                    "Methods > Metagenomic sequencing",
                ),
            )
            connection.execute(
                """
                INSERT INTO claims(
                    paper_id, statement, claim_type, author_strength, scope,
                    artifact_id, source_locator
                ) VALUES (?, ?, 'association', 'strong', ?, ?, ?)
                """,
                (
                    "P000001",
                    "Blautia A increases during altitude relocation.",
                    "Human relocation cohort",
                    artifact_id,
                    "Results > Blautia A; Fig. 2",
                ),
            )
            connection.execute(
                """
                INSERT INTO change_log(
                    timestamp, action, entity_type, entity_id, paper_id, summary
                ) VALUES (?, 'ADD', 'paper', 'P000001', 'P000001', 'Paper registered')
                """,
                (now,),
            )
            connection.execute(
                """
                INSERT INTO issues(
                    paper_id, category, nature, target_type, target_id, assessment,
                    basis, severity, confidence, why_it_matters, artifact_id,
                    source_locator, created_at
                ) VALUES (?, 'causal_inference', 'scope_limitation', 'claim', '1', ?,
                          'demonstrated', 'major', 'high', ?, ?, ?, ?)
                """,
                (
                    "P000001",
                    "Relocation is bundled with environmental change.",
                    "Human association does not isolate hypoxia causation.",
                    artifact_id,
                    "Methods > Study design",
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id,
                    confidence, note, created_at
                ) VALUES ('claim', '1', 'QUALIFIES', 'issue', '1', 'high', ?, ?)
                """,
                (
                    "The limitation bounds the causal interpretation.",
                    now,
                ),
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_search_knowledge_returns_ranked_structured_matches(self) -> None:
        result = search_knowledge(self.root, "Blautia altitude", limit=10)

        self.assertTrue(result["ok"])
        self.assertEqual(result["query"], "Blautia altitude")
        self.assertGreaterEqual(len(result["results"]), 1)
        self.assertTrue(
            any(item["entity_type"] == "claim" for item in result["results"])
        )
        self.assertTrue(all("retrieval_rank" in item for item in result["results"]))

    def test_list_entities_filters_by_entity_type_and_query(self) -> None:
        result = list_entities(self.root, "method", query="shotgun", limit=10)

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["name"], "Shotgun metagenomics")
        self.assertEqual(
            result["results"][0]["source_locator"],
            "Methods > Metagenomic sequencing",
        )

    def test_evidence_packet_returns_units_and_relations_without_judging_strength(self) -> None:
        result = evidence_packet(self.root, "Blautia altitude", limit=10)

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["evidence_units"]), 1)
        self.assertEqual(result["relations"][0]["predicate"], "QUALIFIES")
        self.assertIn("不代表科研结论强度判断", result["note"])

    def test_related_papers_returns_cross_paper_relation(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, created_at, updated_at
                ) VALUES ('P000002', 'Related cohort paper', '10.1234/related',
                          'doi:10.1234/related', ?, ?)
                """,
                (now, now),
            )
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id,
                    confidence, note, created_at
                ) VALUES ('paper', 'P000001', 'SHARES_DATA_WITH', 'paper', 'P000002',
                          'high', 'Same deposited cohort data.', ?)
                """,
                (now,),
            )

        result = related_papers(self.root, "P000001")

        self.assertEqual(len(result["related"]), 1)
        self.assertEqual(result["related"][0]["paper"]["id"], "P000002")
        self.assertEqual(
            result["related"][0]["relations"][0]["predicate"], "SHARES_DATA_WITH"
        )

    def test_paper_history_returns_semantic_change_log(self) -> None:
        result = paper_history(self.root, "P000001")

        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["history"][0]["summary"], "Paper registered")

    def test_get_paper_returns_identity_artifacts_and_knowledge_counts(self) -> None:
        result = get_paper(self.root, "P000001")

        self.assertEqual(result["paper"]["doi"], "10.1234/altitude")
        self.assertEqual(len(result["artifacts"]), 1)
        self.assertEqual(result["counts"]["claims"], 1)
        self.assertEqual(result["counts"]["issues"], 1)


if __name__ == "__main__":
    unittest.main()
