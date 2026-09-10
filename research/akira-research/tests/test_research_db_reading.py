from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database, validate  # noqa: E402
from research_db_ops.acquisition import record_acquisition_attempt  # noqa: E402
from research_db_critical import ingest_critical  # noqa: E402
from research_db_ingest import add_paper_artifacts, ingest_paper  # noqa: E402
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
        supplement = incoming / "supplement.pdf"
        supplement.write_bytes(b"%PDF-1.4\nsupplement-test\n")
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
                    },
                    {
                        "kind": "supplementary_material",
                        "path": str(supplement),
                        "source": "publisher",
                        "source_url": "https://example.test/supplement.pdf",
                    },
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
            "extraction_checks": {"observation_semantics_checked": True},
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
                    "source_locator": "Discussion > Interpretation",
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
                    "predicate": "INDIRECTLY_SUPPORTS",
                    "object_type": "claim",
                    "object_ref": "claim-1",
                    "note": "Human longitudinal association is directionally consistent but does not itself establish causality.",
                },
            ],
        }

    def test_reconstruction_bundle_is_atomic_and_updates_paper_state(self) -> None:
        result = ingest_reading(self.root, self.reconstruction_bundle())

        self.assertEqual(result["reading_status"], "reconstructed")
        self.assertEqual(result["counts"]["methods"], 1)
        self.assertEqual(result["counts"]["relations"], 2)
        self.assertIn("claim:claim-1", result["refs"])

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
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
                "predicate": "DIRECTLY_SUPPORTS",
                "object_type": "claim",
                "object_ref": "claim-1",
            }
        )

        with self.assertRaisesRegex(RuntimeError, "未知 bundle ref"):
            ingest_reading(self.root, bundle)

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            counts = tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("methods", "experiments", "observations", "claims", "leads", "relations", "reading_runs")
            )
            paper = connection.execute(
                "SELECT reading_status FROM papers WHERE id='P000001'"
            ).fetchone()[0]
        self.assertEqual(counts, (0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(paper, "unread")

    def test_ambiguous_support_relation_is_rejected(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["relations"][1]["predicate"] = "SUPPORTS"
        bundle["relations"][1].pop("note", None)

        with self.assertRaisesRegex(RuntimeError, "不得使用模糊 SUPPORTS"):
            ingest_reading(self.root, bundle)

    def test_indirect_support_requires_boundary_note(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["relations"][1].pop("note")

        with self.assertRaisesRegex(RuntimeError, "必须说明证据边界"):
            ingest_reading(self.root, bundle)

    def test_knowledge_unit_requires_source_locator(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["observations"][0].pop("source_locator")

        with self.assertRaisesRegex(RuntimeError, "Observation 必须提供 source_locator"):
            ingest_reading(self.root, bundle)

    def test_vague_source_locator_is_rejected(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["claims"][0]["source_locator"] = "Discussion"

        with self.assertRaisesRegex(RuntimeError, "source_locator=.*过于模糊"):
            ingest_reading(self.root, bundle)

    def test_reconstruction_requires_observation_semantics_self_audit(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle.pop("extraction_checks")

        with self.assertRaisesRegex(RuntimeError, "extraction_checks"):
            ingest_reading(self.root, bundle)

    def test_deep_extraction_requires_quantitative_evidence_contract(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "checked",
            "supplement_presence": "present",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code or data repository is part of this synthetic test paper.",
            "quantitative_results_present": True,
        }

        with self.assertRaisesRegex(RuntimeError, "至少一个 Observation"):
            ingest_reading(self.root, bundle)

        bundle["observations"][0]["statistics"] = {"n": 45, "p_value": 0.01}
        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        result = ingest_reading(self.root, bundle)
        self.assertEqual(result["depth"], "deep_extraction")

    def test_deep_extraction_requires_reason_for_not_applicable_status(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "not_applicable",
            "supplement_presence": "none_found",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code/data repository is reported in this synthetic paper.",
            "quantitative_results_present": True,
        }

        with self.assertRaisesRegex(RuntimeError, "supplement_reason"):
            ingest_reading(self.root, bundle)

    def test_deep_extraction_rejects_not_applicable_when_supplement_is_registered(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "not_applicable",
            "supplement_presence": "none_found",
            "supplement_reason": "The supplement looks unrelated.",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code/data repository is reported in this synthetic paper.",
            "quantitative_results_present": True,
        }

        with self.assertRaisesRegex(RuntimeError, "supplement_presence"):
            ingest_reading(self.root, bundle)

    def test_deep_extraction_checked_supplement_must_be_in_artifacts_checked(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "checked",
            "supplement_presence": "present",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code/data repository is reported in this synthetic paper.",
            "quantitative_results_present": True,
        }

        with self.assertRaisesRegex(RuntimeError, "artifacts_checked.*supplement artifact"):
            ingest_reading(self.root, bundle)

        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        result = ingest_reading(self.root, bundle)
        self.assertEqual(result["depth"], "deep_extraction")

    def test_deep_extraction_access_limited_supplement_requires_attempt_provenance(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "access_limited",
            "supplement_presence": "present",
            "supplement_reason": "An additional referenced supplement could not yet be retrieved.",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code/data repository is reported in this synthetic paper.",
            "quantitative_results_present": True,
            "supplement_attempt_ids": [999],
        }
        with self.assertRaisesRegex(RuntimeError, "Acquisition Attempt provenance"):
            ingest_reading(self.root, bundle)

        attempts = []
        for payload in (
            {
                "paper_id": "P000001",
                "target_kind": "supplement",
                "target_label": "Supplementary Table 2",
                "route_family": "publisher",
                "resource_kind": "supplement",
                "source_url": "https://publisher.example/supp2.pdf",
                "outcome": "access_denied",
                "detail": "Direct supplementary PDF returned access denial.",
            },
            {
                "paper_id": "P000001",
                "target_kind": "supplement",
                "target_label": "Supplementary Table 2",
                "route_family": "open_index",
                "resource_kind": "repository_record",
                "source_url": "https://open-index.example/supp2",
                "outcome": "not_found",
                "detail": "Open repository resolution did not expose the referenced supplement.",
            },
        ):
            attempts.append(record_acquisition_attempt(self.root, payload)["attempt"]["id"])
        bundle["extraction_checks"]["supplement_attempt_ids"] = attempts
        result = ingest_reading(self.root, bundle)
        self.assertEqual(result["depth"], "deep_extraction")

    def test_deep_extraction_rejects_none_found_when_main_text_exposes_public_data(self) -> None:
        xml_path = self.root / "literature" / "papers" / "P000001" / "data-availability.xml"
        xml_path.write_text(
            "<article><sec><title>Availability of data and materials</title>"
            "<p>The data are publicly available at "
            "<ext-link href='https://repository.example/data.xlsx'>repository</ext-link>."
            "</p></sec></article>",
            encoding="utf-8",
        )
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                """
                UPDATE artifacts
                SET path = ?, content_type = 'application/xml',
                    source_url = 'https://publisher.example/data.xml'
                WHERE paper_id = 'P000001' AND kind = 'main_text'
                """,
                (str(xml_path.relative_to(self.root)),),
            )

        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "checked",
            "supplement_presence": "present",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code or data was noticed during reading.",
            "quantitative_results_present": True,
        }
        with self.assertRaisesRegex(RuntimeError, "主文明确暴露代码/数据获取位置"):
            ingest_reading(self.root, bundle)

    def test_deep_extraction_checked_code_data_requires_acquired_attempt(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "checked",
            "supplement_presence": "present",
            "code_data_status": "checked",
            "code_data_presence": "present",
            "code_data_attempt_ids": [999],
            "quantitative_results_present": True,
        }
        with self.assertRaisesRegex(RuntimeError, "code_data.*provenance"):
            ingest_reading(self.root, bundle)

        attempt_id = record_acquisition_attempt(
            self.root,
            {
                "paper_id": "P000001",
                "target_kind": "code_data",
                "target_label": "Public analysis dataset",
                "route_family": "repository",
                "resource_kind": "repository_record",
                "source_url": "https://repository.example/data.xlsx",
                "outcome": "acquired",
                "detail": "The public dataset was retrieved and inspected for the deep extraction.",
            },
        )["attempt"]["id"]
        bundle["extraction_checks"]["code_data_attempt_ids"] = [attempt_id]
        result = ingest_reading(self.root, bundle)
        self.assertEqual(result["depth"], "deep_extraction")

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

    def test_critical_audit_cannot_upgrade_full_scan_to_deep_extraction(self) -> None:
        ingest_reading(self.root, self.reconstruction_bundle())
        with self.assertRaisesRegex(RuntimeError, "不能把 full_scan Reconstruction 升级"):
            ingest_critical(
                self.root,
                {
                    "paper_id": "P000001",
                    "depth": "deep_extraction",
                    "artifacts_checked": [{"artifact_kind": "main_text"}],
                    "sections_checked": ["Methods", "Discussion"],
                    "issues": [],
                },
            )

    def test_critical_issue_requires_basis_rationale(self) -> None:
        reading = ingest_reading(self.root, self.reconstruction_bundle())
        claim_id = reading["refs"]["claim:claim-1"]
        with self.assertRaisesRegex(RuntimeError, "basis_rationale"):
            ingest_critical(
                self.root,
                {
                    "paper_id": "P000001",
                    "artifacts_checked": [{"artifact_kind": "main_text"}],
                    "sections_checked": ["Methods", "Discussion"],
                    "issues": [
                        {
                            "ref": "issue-1",
                            "category": "population_scope",
                            "nature": "scope_limitation",
                            "target_type": "claim",
                            "target_id": claim_id,
                            "assessment": "The sampled cohort has a defined scope.",
                            "basis": "demonstrated",
                            "severity": "moderate",
                            "confidence": "high",
                            "artifact_kind": "main_text",
                            "source_locator": "Methods > Participants",
                        }
                    ],
                },
            )

    def test_late_supplement_reopens_and_can_refresh_deep_review(self) -> None:
        bundle = self.reconstruction_bundle()
        bundle["depth"] = "deep_extraction"
        bundle["observations"][0]["statistics"] = {"n": 45}
        bundle["artifacts_checked"].append({"artifact_kind": "supplementary_material"})
        bundle["extraction_checks"] = {
            "observation_semantics_checked": True,
            "figures_tables_checked": True,
            "quantitative_results_checked": True,
            "supplement_status": "checked",
            "supplement_presence": "present",
            "code_data_status": "not_applicable",
            "code_data_presence": "none_found",
            "code_data_reason": "No code/data repository is reported in this synthetic paper.",
            "quantitative_results_present": True,
        }
        ingest_reading(self.root, bundle)
        ingest_critical(
            self.root,
            {
                "paper_id": "P000001",
                "depth": "deep_extraction",
                "artifacts_checked": [
                    {"artifact_kind": "main_text"},
                    {"artifact_kind": "supplementary_material"},
                ],
                "sections_checked": ["Methods", "Results", "Discussion", "Supplement"],
                "issues": [],
            },
        )

        late = self.root / "incoming" / "late-supplement.csv"
        late.write_text("metric,value\nexample,1\n", encoding="utf-8")
        added = add_paper_artifacts(
            self.root,
            {
                "paper_id": "P000001",
                "artifacts": [
                    {"kind": "supplementary_table", "path": str(late)}
                ],
                "reason": "Late supplementary table became available",
            },
        )
        late_id = added["artifacts"][0]["id"]

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            state = connection.execute(
                "SELECT reading_status, critical_status FROM papers WHERE id = 'P000001'"
            ).fetchone()
            supplement_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM artifacts WHERE paper_id = 'P000001' AND kind LIKE 'supplement%' ORDER BY id"
                )
            ]
            main_id = connection.execute(
                "SELECT id FROM artifacts WHERE paper_id = 'P000001' AND kind = 'main_text'"
            ).fetchone()[0]
        self.assertEqual(state, ("unread", "not_reviewed"))
        self.assertTrue(validate(self.root)["ok"], "late artifact should invalidate review state, not historical integrity")

        refreshed = ingest_reading(
            self.root,
            {
                "paper_id": "P000001",
                "depth": "deep_extraction",
                "artifacts_checked": [
                    {"artifact_id": main_id},
                    *[{"artifact_id": artifact_id} for artifact_id in supplement_ids],
                ],
                "sections_checked": ["Supplementary table refresh"],
                "extraction_checks": {
                    "observation_semantics_checked": True,
                    "figures_tables_checked": True,
                    "quantitative_results_checked": True,
                    "supplement_status": "checked",
                    "supplement_presence": "present",
                    "code_data_status": "not_applicable",
                    "code_data_presence": "none_found",
                    "code_data_reason": "No new code/data locator was present in the late supplement.",
                    "quantitative_results_present": False,
                    "quantitative_results_reason": "The late table adds no result relevant to the current evidence chain.",
                },
                "methods": [],
                "experiments": [],
                "observations": [],
                "claims": [],
                "leads": [],
            },
        )
        self.assertEqual(refreshed["counts"]["observations"], 0)
        self.assertIn(late_id, supplement_ids)

        audit = ingest_critical(
            self.root,
            {
                "paper_id": "P000001",
                "depth": "deep_extraction",
                "artifacts_checked": [{"artifact_id": late_id}],
                "sections_checked": ["Supplementary table refresh"],
                "issues": [],
            },
        )
        self.assertEqual(audit["reading_status"], "extracted")
        self.assertEqual(audit["critical_status"], "critically_reviewed")
        self.assertTrue(validate(self.root)["ok"])

    def test_critical_audit_links_issue_and_sidecar(self) -> None:
        reading = ingest_reading(self.root, self.reconstruction_bundle())
        claim_id = reading["refs"]["claim:claim-1"]
        sidecar = self.root / "literature" / "papers" / "P000001" / "README.md"
        sidecar.write_text("# Reading Test Paper\n\nCritical synthesis.\n", encoding="utf-8")

        result = ingest_critical(
            self.root,
            {
                "paper_id": "P000001",
                "depth": "full_scan",
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
                        "basis_rationale": "The sampled population is explicitly defined in Methods, so the scope limitation is directly established by the study design.",
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

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
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
                "full_scan",
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
