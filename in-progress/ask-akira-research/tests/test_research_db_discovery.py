from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, database_path, init_database, validate  # noqa: E402
from research_db_ops.acquisition import (  # noqa: E402
    list_acquisition_attempts,
    record_acquisition_attempt,
)
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
                "discovery_method": "seed_search",
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
                "discovery_method": "forward_citation",
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

    def test_discovery_search_requires_explicit_discovery_method(self) -> None:
        with self.assertRaisesRegex(ResearchDbError, "discovery_method"):
            record_search_run(
                self.root,
                {
                    "purpose": "Seed search",
                    "mode": "DISCOVERY",
                    "source": "PubMed",
                    "query": "altitude microbiome",
                    "candidates": [],
                },
            )

    def test_exact_work_only_does_not_require_saturation_citation_chasing(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Retrieve two user-specified papers",
                "discovery_method": "exact_work",
                "source": "Crossref",
                "query": "two exact titles",
                "candidates": [
                    {
                        "title": "Known paper one",
                        "doi": "10.1234/known-one",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    },
                    {
                        "title": "Known paper two",
                        "doi": "10.1234/known-two",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    },
                ],
            },
        )
        for item in result["persisted_candidates"]:
            candidate_id = item["id"]
            record_acquisition_attempt(
                self.root,
                {
                    "candidate_id": candidate_id,
                    "target_kind": "main_text",
                    "route_family": "publisher",
                    "resource_kind": "article_page",
                    "source_url": f"https://publisher.example/{candidate_id}",
                    "outcome": "access_denied",
                    "detail": "Publisher route did not expose retrievable full text.",
                },
            )
            record_acquisition_attempt(
                self.root,
                {
                    "candidate_id": candidate_id,
                    "target_kind": "main_text",
                    "route_family": "open_index",
                    "resource_kind": "repository_record",
                    "source_url": f"https://open-index.example/{candidate_id}",
                    "outcome": "not_found",
                    "detail": "Open-access resolver found no alternate full-text location.",
                },
            )
            update_candidate(
                self.root,
                candidate_id,
                {
                    "user_access_status": "unavailable_to_user",
                    "user_access_reason": "User-assisted access was attempted but no authorized copy was available.",
                },
            )
            update_candidate(self.root, candidate_id, {"acquisition_status": "unavailable"})

        readiness = discovery_readiness(self.root)
        self.assertTrue(readiness["ready_for_saturation"])
        self.assertEqual(readiness["discovery_families"], [])
        self.assertEqual(readiness["citation_chasing_count"], 0)

    def test_relevant_candidate_defaults_to_acquisition_queue(self) -> None:
        record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "discovery_method": "seed_search",
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
                "discovery_method": "related_work",
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
                "discovery_method": "seed_search",
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
                "discovery_method": "seed_search",
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

    def test_user_assisted_access_is_completed_when_full_text_is_ingested(self) -> None:
        recorded = record_search_run(
            self.root,
            {
                "purpose": "Known subscription paper",
                "discovery_method": "exact_work",
                "source": "Crossref",
                "query": "10.1234/user-assisted",
                "candidates": [
                    {
                        "title": "User assisted paper",
                        "doi": "10.1234/user-assisted",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    }
                ],
            },
        )
        candidate_id = recorded["persisted_candidates"][0]["id"]
        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "authenticated",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/subscription-paper",
                "outcome": "auth_required",
                "detail": "The full text requires the user's authorized institutional login.",
            },
        )
        waiting = list_candidates(self.root)["candidates"][0]
        self.assertEqual(waiting["user_access_status"], "required")
        self.assertIn(
            "user_access_action_required",
            {item["reason"] for item in discovery_readiness(self.root)["blockers"]},
        )

        source = self.root / "authorized-paper.html"
        source.write_text("<html><body>authorized full text</body></html>", encoding="utf-8")
        ingest_paper(
            self.root,
            {
                "title": "User assisted paper",
                "doi": "10.1234/user-assisted",
                "artifacts": [
                    {
                        "kind": "main_text",
                        "path": str(source),
                        "content_type": "text/html",
                        "source": "publisher_authenticated",
                    }
                ],
            },
        )
        acquired = list_candidates(self.root)["candidates"][0]
        self.assertEqual(acquired["acquisition_status"], "acquired")
        self.assertEqual(acquired["user_access_status"], "completed")

    def test_identity_resolution_reuses_title_match_despite_punctuation(self) -> None:
        first = record_search_run(
            self.root,
            {
                "purpose": "Seed search",
                "discovery_method": "seed_search",
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
                "discovery_method": "exact_work",
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
                "discovery_method": "seed_search",
                "source": "Web",
                "query": "paper a",
                "candidates": [{"title": "Paper A", "year": 2024}],
            },
        )
        second = record_search_run(
            self.root,
            {
                "purpose": "Independent identity result",
                "discovery_method": "exact_work",
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

    def test_discovery_readiness_requires_core_and_high_priority_closure(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Seed",
                "discovery_method": "seed_search",
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
        reasons = {item["reason"] for item in first["blockers"]}
        self.assertIn("core_candidate_not_closed", reasons)
        self.assertIn("high_priority_candidate_not_closed", reasons)
        self.assertIn("citation_chasing_missing", reasons)
        self.assertIn("discovery_strategy_diversity_insufficient", reasons)

        for payload in (
            {
                "candidate_id": core_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/core-paper",
                "outcome": "access_denied",
                "detail": "Publisher article page did not expose accessible full text.",
            },
            {
                "candidate_id": core_id,
                "target_kind": "main_text",
                "route_family": "open_index",
                "resource_kind": "repository_record",
                "source_url": "https://open-index.example/core-paper",
                "outcome": "not_found",
                "detail": "Open-access resolver found no retrievable full-text location.",
            },
        ):
            record_acquisition_attempt(self.root, payload)
        update_candidate(
            self.root,
            core_id,
            {
                "user_access_status": "unavailable_to_user",
                "user_access_reason": "User-assisted access was attempted but no authorized copy was available.",
            },
        )
        update_candidate(self.root, core_id, {"acquisition_status": "unavailable"})
        update_candidate(
            self.root,
            high_id,
            {
                "defer_reason": "A defer reason no longer closes high-priority evidence.",
            },
        )
        still_open = discovery_readiness(self.root)
        self.assertFalse(still_open["ready_for_saturation"])
        self.assertIn(
            "high_priority_candidate_not_closed",
            {item["reason"] for item in still_open["blockers"]},
        )
        for payload in (
            {
                "candidate_id": high_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/high-paper",
                "outcome": "access_denied",
                "detail": "Publisher route did not expose accessible full text.",
            },
            {
                "candidate_id": high_id,
                "target_kind": "main_text",
                "route_family": "repository",
                "resource_kind": "repository_record",
                "source_url": "https://repository.example/high-paper",
                "outcome": "not_found",
                "detail": "Independent repository search found no retrievable full text.",
            },
        ):
            record_acquisition_attempt(self.root, payload)
        update_candidate(
            self.root,
            high_id,
            {
                "user_access_status": "declined",
                "user_access_reason": "User chose not to provide or authenticate access for this test candidate.",
            },
        )
        update_candidate(self.root, high_id, {"acquisition_status": "unavailable"})
        record_search_run(
            self.root,
            {
                "purpose": "Backward citation chase of the core evidence",
                "discovery_method": "backward_citation",
                "source": "OpenAlex",
                "query": "core references",
                "parent_run_id": result["search_run_id"],
                "result_count": 0,
                "what_we_learned": "No additional relevant evidence family was identified.",
                "next_decision": "Close discovery after candidate resolution.",
                "candidates": [],
            },
        )
        readiness = discovery_readiness(self.root)
        self.assertTrue(readiness["ready_for_saturation"])
        self.assertEqual(readiness["citation_chasing_count"], 1)
        self.assertEqual(readiness["discovery_families"], ["citation_chasing", "query_search"])

    def test_unavailable_requires_auditable_access_attempts(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Known core paper",
                "discovery_method": "exact_work",
                "source": "Crossref",
                "query": "10.1234/unavailable-test",
                "candidates": [
                    {
                        "title": "Unavailable test paper",
                        "doi": "10.1234/unavailable-test",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    }
                ],
            },
        )
        candidate_id = result["persisted_candidates"][0]["id"]

        with self.assertRaisesRegex(ResearchDbError, "Acquisition Attempt provenance"):
            update_candidate(self.root, candidate_id, {"acquisition_status": "unavailable"})

        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "pdf",
                "source_url": "https://publisher.example/paper.pdf",
                "outcome": "access_denied",
                "detail": "Direct PDF returned access denial.",
            },
        )
        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "open_index",
                "resource_kind": "repository_record",
                "source_url": "https://open-index.example/10.1234/unavailable-test",
                "outcome": "not_found",
                "detail": "Open-access resolver did not identify a retrievable copy.",
            },
        )
        with self.assertRaisesRegex(ResearchDbError, "publisher_pdf_failure_without_article_page_resolution"):
            update_candidate(self.root, candidate_id, {"acquisition_status": "unavailable"})

        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/article",
                "outcome": "auth_required",
                "detail": "Publisher article page requires the user's existing subscription or institutional login.",
            },
        )
        candidate = list_candidates(self.root)["candidates"][0]
        self.assertEqual(candidate["user_access_status"], "required")
        with self.assertRaisesRegex(ResearchDbError, "等待用户协同"):
            update_candidate(self.root, candidate_id, {"acquisition_status": "unavailable"})

        update_candidate(
            self.root,
            candidate_id,
            {
                "user_access_status": "unavailable_to_user",
                "user_access_reason": "User confirmed they do not have authorized access and cannot provide a lawful copy.",
            },
        )
        updated = update_candidate(
            self.root, candidate_id, {"acquisition_status": "unavailable"}
        )
        self.assertEqual(updated["candidate"]["acquisition_status"], "unavailable")

    def test_acquisition_attempt_correction_must_supersede_false_acquired_result(self) -> None:
        result = record_search_run(
            self.root,
            {
                "purpose": "Known paper",
                "discovery_method": "exact_work",
                "source": "Crossref",
                "query": "10.1234/correction-test",
                "candidates": [
                    {
                        "title": "Correction test paper",
                        "doi": "10.1234/correction-test",
                        "relevance_status": "relevant",
                        "reading_priority": "core",
                    }
                ],
            },
        )
        candidate_id = result["persisted_candidates"][0]["id"]
        acquired = record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "full_text_html",
                "source_url": "https://publisher.example/article",
                "outcome": "acquired",
                "detail": "Initial inspection incorrectly classified a subscription preview as full text.",
            },
        )["attempt"]
        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "open_index",
                "resource_kind": "repository_record",
                "source_url": "https://open-index.example/correction-test",
                "outcome": "not_found",
                "detail": "Independent open resolver found no full-text copy.",
            },
        )

        with self.assertRaisesRegex(ResearchDbError, "unavailable_has_active_acquired_attempt"):
            update_candidate(self.root, candidate_id, {"acquisition_status": "unavailable"})

        correction = record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/article",
                "outcome": "invalid_artifact",
                "detail": "Reinspection confirmed that the page is only a subscription preview and lacks the full Methods/Results body.",
                "supersedes_attempt_ids": [acquired["id"]],
                "supersession_reason": "The original acquired classification was false after full-text boundary verification.",
            },
        )["attempt"]
        update_candidate(
            self.root,
            candidate_id,
            {
                "user_access_status": "unavailable_to_user",
                "user_access_reason": "User-assisted access was attempted after the false positive was corrected, but no authorized full text was available.",
            },
        )
        updated = update_candidate(
            self.root, candidate_id, {"acquisition_status": "unavailable"}
        )
        self.assertEqual(updated["candidate"]["acquisition_status"], "unavailable")

        attempts = list_acquisition_attempts(self.root, candidate_id=candidate_id)["attempts"]
        original = next(item for item in attempts if item["id"] == acquired["id"])
        self.assertEqual(original["validity_status"], "superseded")
        self.assertEqual(original["superseded_by_attempt_id"], correction["id"])
        self.assertIn("false", original["supersession_reason"])

        final_correction = record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate_id,
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/article?verified=1",
                "outcome": "invalid_artifact",
                "detail": "A later verification refines the correction while preserving the same final access conclusion.",
                "supersedes_attempt_ids": [correction["id"]],
                "supersession_reason": "Later verification supersedes the intermediate correction record.",
            },
        )["attempt"]
        self.assertGreater(final_correction["id"], correction["id"])
        self.assertTrue(validate(self.root)["ok"])

    def test_acquisition_attempt_correction_requires_same_target(self) -> None:
        first = record_search_run(
            self.root,
            {
                "purpose": "Known papers",
                "discovery_method": "exact_work",
                "source": "Crossref",
                "query": "two papers",
                "candidates": [
                    {"title": "Paper A", "doi": "10.1234/a"},
                    {"title": "Paper B", "doi": "10.1234/b"},
                ],
            },
        )
        a_id, b_id = [item["id"] for item in first["persisted_candidates"]]
        attempt_id = record_acquisition_attempt(
            self.root,
            {
                "candidate_id": a_id,
                "route_family": "publisher",
                "resource_kind": "article_page",
                "source_url": "https://publisher.example/a",
                "outcome": "acquired",
                "detail": "Initial result.",
            },
        )["attempt"]["id"]
        with self.assertRaisesRegex(ResearchDbError, "不属于 Candidate"):
            record_acquisition_attempt(
                self.root,
                {
                    "candidate_id": b_id,
                    "route_family": "publisher",
                    "resource_kind": "article_page",
                    "source_url": "https://publisher.example/b",
                    "outcome": "invalid_artifact",
                    "detail": "Correction for another candidate should be rejected.",
                    "supersedes_attempt_ids": [attempt_id],
                    "supersession_reason": "Wrong target.",
                },
            )

    def test_search_run_cannot_create_unavailable_without_attempt_provenance(self) -> None:
        with self.assertRaisesRegex(ResearchDbError, "不能直接创建.*unavailable"):
            record_search_run(
                self.root,
                {
                    "purpose": "Known paper",
                    "discovery_method": "exact_work",
                    "source": "Crossref",
                    "query": "10.1234/no-shortcut",
                    "candidates": [
                        {
                            "title": "No shortcut paper",
                            "doi": "10.1234/no-shortcut",
                            "relevance_status": "relevant",
                            "acquisition_status": "unavailable",
                        }
                    ],
                },
            )

    def test_record_search_rejects_missing_parent_run(self) -> None:
        with self.assertRaises(ResearchDbError):
            record_search_run(
                self.root,
                {
                    "purpose": "Expansion",
                    "discovery_method": "query_expansion",
                    "source": "PubMed",
                    "query": "Blautia",
                    "parent_run_id": 999,
                },
            )


if __name__ == "__main__":
    unittest.main()
