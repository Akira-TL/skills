from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import init_database, validate  # noqa: E402
from research_db_critical import ingest_critical  # noqa: E402
from research_db_ingest import ingest_paper  # noqa: E402
from research_db_ops.acquisition import record_acquisition_attempt  # noqa: E402
from research_db_ops.candidates import list_candidates  # noqa: E402
from research_db_ops.discovery import record_search_run  # noqa: E402
from research_db_ops.query import evidence_packet  # noqa: E402
from research_db_ops.relations import add_relation  # noqa: E402
from research_db_reading import ingest_reading  # noqa: E402


class LiteratureWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        self.incoming = self.root / "incoming"
        self.incoming.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _acquire(self, title: str, doi: str, filename: str) -> str:
        artifact = self.incoming / filename
        artifact.write_text(f"<html><body>{title}</body></html>", encoding="utf-8")
        candidate = next(
            item for item in list_candidates(self.root)["candidates"]
            if item.get("doi") == doi
        )
        record_acquisition_attempt(
            self.root,
            {
                "candidate_id": candidate["id"],
                "target_kind": "main_text",
                "route_family": "publisher",
                "resource_kind": "full_text_html",
                "source_url": f"https://publisher.example/{doi}",
                "outcome": "acquired",
                "detail": "Publisher-hosted full text retrieved and verified for integration test.",
            },
        )
        result = ingest_paper(
            self.root,
            {
                "title": title,
                "doi": doi,
                "artifacts": [
                    {
                        "kind": "main_text",
                        "path": str(artifact),
                        "content_type": "text/html",
                        "source": "publisher",
                    }
                ],
            },
        )
        return result["paper_id"]

    def _read_and_audit(self, paper_id: str, statement: str, claim: str) -> None:
        reading = ingest_reading(
            self.root,
            {
                "paper_id": paper_id,
                "depth": "full_scan",
                "artifacts_checked": [{"artifact_kind": "main_text"}],
                "sections_checked": ["Methods", "Results", "Discussion"],
                "extraction_checks": {"observation_semantics_checked": True},
                "experiments": [
                    {
                        "ref": "experiment-1",
                        "question": "Is marker X associated with adaptation?",
                        "design": "observational cohort",
                        "samples": "participant samples",
                        "artifact_kind": "main_text",
                        "source_locator": "Methods > Study design",
                    }
                ],
                "observations": [
                    {
                        "ref": "observation-1",
                        "experiment_ref": "experiment-1",
                        "statement": statement,
                        "effect": "marker X differed with adaptation status",
                        "artifact_kind": "main_text",
                        "source_locator": "Results > Marker X",
                    }
                ],
                "claims": [
                    {
                        "ref": "claim-1",
                        "statement": claim,
                        "claim_type": "causal",
                        "author_strength": "strong",
                        "artifact_kind": "main_text",
                        "source_locator": "Discussion > Interpretation",
                    }
                ],
                "relations": [
                    {
                        "subject_type": "observation",
                        "subject_ref": "observation-1",
                        "predicate": "INDIRECTLY_SUPPORTS",
                        "object_type": "claim",
                        "object_ref": "claim-1",
                        "note": "The observational design is compatible with the claim but does not establish causality.",
                    }
                ],
            },
        )
        claim_id = reading["refs"]["claim:claim-1"]
        ingest_critical(
            self.root,
            {
                "paper_id": paper_id,
                "artifacts_checked": [{"artifact_kind": "main_text"}],
                "sections_checked": ["Methods", "Results", "Discussion"],
                "issues": [
                    {
                        "ref": "issue-1",
                        "category": "causal_inference",
                        "nature": "scope_limitation",
                        "target_type": "claim",
                        "target_id": claim_id,
                        "assessment": "The observational design does not identify an independent causal effect of marker X.",
                        "basis": "demonstrated",
                        "basis_rationale": "The observational design is directly reported in Methods, so the inference limit is an established design fact rather than a hypothetical risk.",
                        "severity": "major",
                        "confidence": "high",
                        "why_it_matters": "The causal claim must remain indirect.",
                        "artifact_kind": "main_text",
                        "source_locator": "Methods > Study design",
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

    def test_problem_driven_multi_paper_workflow_is_auditable_end_to_end(self) -> None:
        seed = record_search_run(
            self.root,
            {
                "purpose": "Map evidence for marker X and human adaptation",
                "discovery_method": "seed_search",
                "source": "literature-index-a",
                "query": "marker X human adaptation",
                "what_we_learned": "Two longitudinal cohort papers use the same deposited dataset.",
                "next_decision": "Acquire both and verify whether they are independent evidence.",
                "candidates": [
                    {
                        "title": "Marker X cohort discovery",
                        "doi": "10.1234/marker-one",
                        "relevance_status": "relevant",
                        "relevance_reason": "Direct cohort evidence.",
                        "reading_priority": "core",
                    },
                    {
                        "title": "Marker X companion analysis",
                        "doi": "10.1234/marker-two",
                        "relevance_status": "relevant",
                        "relevance_reason": "Potential replication or dataset reuse.",
                        "reading_priority": "high",
                    },
                ],
            },
        )
        record_search_run(
            self.root,
            {
                "purpose": "Citation and terminology expansion",
                "discovery_method": "backward_citation",
                "source": "literature-index-b",
                "query": "10.1234/marker-one related work",
                "parent_run_id": seed["search_run_id"],
                "what_we_learned": "The first paper reappears; this is not a new independent study.",
                "next_decision": "Deduplicate and read the two unique papers.",
                "candidates": [
                    {
                        "title": "Marker X cohort discovery",
                        "doi": "10.1234/marker-one",
                        "relevance_status": "relevant",
                    }
                ],
            },
        )
        candidates = list_candidates(self.root)["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(item["acquisition_status"] == "queued" for item in candidates))
        self.assertEqual(len(candidates[0]["search_runs"]), 2)

        paper_one = self._acquire(
            "Marker X cohort discovery", "10.1234/marker-one", "one.html"
        )
        paper_two = self._acquire(
            "Marker X companion analysis", "10.1234/marker-two", "two.html"
        )
        self._read_and_audit(
            paper_one,
            "Marker X was higher in participants with stronger adaptation.",
            "Marker X contributes causally to human adaptation.",
        )
        self._read_and_audit(
            paper_two,
            "Marker X tracked the same adaptation phenotype in a companion analysis.",
            "Marker X is a causal driver of human adaptation.",
        )
        add_relation(
            self.root,
            {
                "subject_type": "paper",
                "subject_id": paper_one,
                "predicate": "SHARES_DATA_WITH",
                "object_type": "paper",
                "object_id": paper_two,
                "confidence": "high",
                "note": "Both papers use the same deposited participant dataset; they are not independent replication.",
            },
        )

        packet = evidence_packet(self.root, "marker adaptation", limit=20)
        self.assertEqual({paper["id"] for paper in packet["papers"]}, {paper_one, paper_two})
        self.assertEqual(len(packet["evidence_families"]), 1)
        self.assertEqual(
            packet["evidence_families"][0]["paper_ids"], [paper_one, paper_two]
        )
        self.assertTrue(
            any(unit["entity_type"] == "issue" for unit in packet["evidence_units"])
        )
        self.assertTrue(validate(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
