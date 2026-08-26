from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, database_path, init_database  # noqa: E402
from research_db_ops.candidates import (  # noqa: E402
    discovery_readiness,
    list_candidates,
    merge_candidates,
    update_candidate,
)
from research_db_ops.discovery import list_search_runs, record_search_run  # noqa: E402
from research_db_ingest import ingest_paper  # noqa: E402


class ResearchDbDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_record_search_persists_run_candidates_and_deduplicates_identity(self) -> None:
        first = record_search_run(
            self.root,
            {
                "purpose": "Find human altitude microbiome evidence",
                "mode": "DISCOVERY",
                "source": "PubMed",
                "query": "altitude gut microbiome Blautia",
                "filters": {"language": "English"},
                "what_we_learned": "Blautia is a recurring term.",
                "next_decision": "Chase related longitudinal studies.",
                "result_count": 20,
                "candidates": [
                    {
                        "title": "Altitude gut microbiome study",
                        "doi": "https://doi.org/10.1234/ALTITUDE",
                        "authors": ["A. Author", "B. Author"],
                        "year": 2024,
                        "source_url": "https://example.test/paper",
                        "source_result_id": "123",
                        "result_rank": 1,
                        "relevance_status": "relevant",
                        "relevance_reason": "Direct human longitudinal study.",
                        "reading_priority": "core",
                        "acquisition_status": "queued",
                    }
                ],
            },
        )
        second = record_search_run(
            self.root,
            {
                "purpose": "Forward citation chase",
                "source": "OpenAlex",
                "query": "10.1234/altitude cited_by",
                "parent_run_id": first["search_run_id"],
                "candidates": [
                    {
                        "title": "Altitude gut microbiome study",
                        "doi": "10.1234/altitude",
                        "year": 2024,
                        "result_rank": 3,
                    }
                ],
            },
        )

        self.assertEqual(first["persisted_candidates"][0]["action"], "created")
        self.assertEqual(second["persisted_candidates"][0]["action"], "reused")
        candidates = list_candidates(self.root)["candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["doi"], "10.1234/altitude")
        self.assertEqual(candidates[0]["reading_priority"], "core")
        self.assertEqual(len(candidates[0]["search_runs"]), 2)
        self.assertEqual(len(list_search_runs(self.root)["search_runs"]), 2)

    def test_relevant_candidate_defaults_to_acquisition_queue(self) -> None:
        record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "source": "PubMed",
                "query": "altitude microbiome",
                "candidates": [
                    {
                        "title": "Relevant paper",
                        "relevance_status": "relevant",
                        "relevance_reason": "Directly studies the target population.",
                    }
                ],
            },
        )

        candidate = list_candidates(self.root)["candidates"][0]
        self.assertEqual(candidate["acquisition_status"], "queued")

    def test_existing_paper_marks_discovered_candidate_acquired(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, canonical_identity, status, created_at, updated_at
                ) VALUES ('P000001', 'Known paper', '10.1234/known',
                          'doi:10.1234/known', 'active', ?, ?)
                """,
                (now, now),
            )

        result = record_search_run(
            self.root,
            {
                "purpose": "Related work",
                "source": "Crossref",
                "query": "known paper",
                "candidates": [
                    {"title": "Known paper", "doi": "10.1234/known", "year": 2024}
                ],
            },
        )
        candidate_id = result["persisted_candidates"][0]["id"]
        candidate = list_candidates(self.root)["candidates"][0]
        self.assertEqual(candidate["id"], candidate_id)
        self.assertEqual(candidate["paper_id"], "P000001")
        self.assertEqual(candidate["acquisition_status"], "acquired")
        self.assertEqual(candidate["identity_status"], "resolved")

    def test_excluded_candidate_requires_reason(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "source": "PubMed",
                "query": "altitude microbiome",
                "candidates": [{"title": "Possibly relevant result"}],
            },
        )
        candidate_id = result["persisted_candidates"][0]["id"]

        with self.assertRaises(ResearchDbError):
            update_candidate(self.root, candidate_id, {"relevance_status": "excluded"})

        updated = update_candidate(
            self.root,
            candidate_id,
            {
                "relevance_status": "excluded",
                "exclusion_reason": "Not a scholarly research article on the target question.",
            },
        )
        self.assertEqual(updated["candidate"]["relevance_status"], "excluded")

    def test_ingest_paper_links_matching_discovery_candidate(self) -> None:
        recorded = record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "source": "PubMed",
                "query": "altitude microbiome",
                "candidates": [
                    {
                        "title": "Candidate to acquire",
                        "doi": "10.1234/to-acquire",
                        "relevance_status": "relevant",
                        "acquisition_status": "queued",
                    }
                ],
            },
        )
        candidate_id = recorded["persisted_candidates"][0]["id"]
        source = self.root / "source.html"
        source.write_text("<html>paper</html>", encoding="utf-8")

        ingested = ingest_paper(
            self.root,
            {
                "title": "Candidate to acquire",
                "doi": "10.1234/to-acquire",
                "artifacts": [
                    {
                        "kind": "main_text",
                        "path": str(source),
                        "content_type": "text/html",
                    }
                ],
            },
        )

        self.assertEqual(ingested["linked_candidate_ids"], [candidate_id])
        candidate = list_candidates(self.root)["candidates"][0]
        self.assertEqual(candidate["paper_id"], ingested["paper_id"])
        self.assertEqual(candidate["acquisition_status"], "acquired")

    def test_identity_resolution_reuses_title_match_despite_punctuation(self) -> None:
        first = record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "source": "Web",
                "query": "yak microbiome",
                "candidates": [
                    {
                        "title": "Host Bias in Diet-Source Microbiome Transmission in Wild Cohabitating Herbivores",
                        "year": 2021,
                        "relevance_status": "relevant",
                    }
                ],
            },
        )
        second = record_search_run(
            self.root,
            {
                "purpose": "Identity resolution",
                "source": "Europe PMC",
                "query": "exact title",
                "candidates": [
                    {
                        "title": "Host Bias in Diet–Source Microbiome Transmission in Wild Cohabitating Herbivores.",
                        "year": 2021,
                        "doi": "10.1128/spectrum.00756-21",
                        "relevance_status": "relevant",
                    }
                ],
            },
        )

        self.assertEqual(first["persisted_candidates"][0]["id"], second["persisted_candidates"][0]["id"])
        self.assertEqual(len(list_candidates(self.root)["candidates"]), 1)

    def test_merge_candidates_preserves_search_provenance(self) -> None:
        first = record_search_run(
            self.root,
            {
                "purpose": "Seed",
                "source": "Web",
                "query": "paper a",
                "candidates": [{"title": "Paper A", "year": 2024}],
            },
        )
        second = record_search_run(
            self.root,
            {
                "purpose": "Independent identity result",
                "source": "Crossref",
                "query": "10.1234/a",
                "candidates": [
                    {
                        "title": "Different indexing title",
                        "year": 2024,
                        "doi": "10.1234/a",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    }
                ],
            },
        )
        keep_id = first["persisted_candidates"][0]["id"]
        merge_id = second["persisted_candidates"][0]["id"]
        merged = merge_candidates(
            self.root,
            keep_id,
            merge_id,
            reason="Exact DOI and manual title verification show the same scholarly work.",
        )

        self.assertTrue(merged["ok"])
        candidates = list_candidates(self.root)["candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["doi"], "10.1234/a")
        self.assertEqual(candidates[0]["reading_priority"], "core")
        self.assertEqual(len(candidates[0]["search_runs"]), 2)

    def test_discovery_readiness_requires_core_closure_and_high_defer_reason(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Seed",
                "source": "Web",
                "query": "yak microbiome",
                "candidates": [
                    {
                        "title": "Core paper",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    },
                    {
                        "title": "High paper",
                        "relevance_status": "relevant",
                        "reading_priority": "high",
                    },
                ],
            },
        )
        core_id = result["persisted_candidates"][0]["id"]
        high_id = result["persisted_candidates"][1]["id"]

        first = discovery_readiness(self.root)
        self.assertFalse(first["ready_for_saturation"])
        self.assertEqual(len(first["blockers"]), 2)

        update_candidate(self.root, core_id, {"acquisition_status": "unavailable"})
        update_candidate(
            self.root,
            high_id,
            {
                "defer_reason": "Additional reading is unlikely to change the current uncertainty boundary.",
            },
        )
        self.assertTrue(discovery_readiness(self.root)["ready_for_saturation"])

    def test_record_search_rejects_missing_parent_run(self) -> None:
        with self.assertRaises(ResearchDbError):
            record_search_run(
                self.root,
                {
                    "purpose": "Expansion",
                    "source": "PubMed",
                    "query": "Blautia",
                    "parent_run_id": 999,
                },
            )


if __name__ == "__main__":
    unittest.main()
