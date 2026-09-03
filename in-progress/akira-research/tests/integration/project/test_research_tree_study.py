from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import init_database, validate  # noqa: E402
from research_db_ops.completion.project import (  # noqa: E402
    planning_completion_readiness,
    research_tree_completion_readiness,
    study_completion_readiness,
)
from research_db_ops.downstream import list_datasets, record_dataset  # noqa: E402
from research_db_ops.planning import list_designs, record_design  # noqa: E402
from research_db_ops.project import (  # noqa: E402
    get_research_tree,
    list_studies,
    record_research_edge,
    record_research_node,
    record_study,
    set_research_tree_state,
)
from research_db_support.storage import ResearchDbError  # noqa: E402


class ResearchTreeStudyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _record_question_tree(self) -> None:
        record_research_node(
            self.root,
            {
                "slug": "objective-root",
                "kind": "objective",
                "label": "Primary objective",
                "workflow_status": "active",
                "branch_priority": "primary",
            },
        )
        record_research_node(
            self.root,
            {
                "slug": "question-main",
                "kind": "question",
                "label": "Primary research question",
                "parent_slug": "objective-root",
                "workflow_status": "active",
                "branch_priority": "primary",
            },
        )
        set_research_tree_state(
            self.root,
            {"root_slug": "objective-root", "active_slug": "question-main"},
        )

    def _write_design(self) -> None:
        (self.root / "designs").mkdir(exist_ok=True)
        (self.root / "designs" / "descriptive.md").write_text(
            "# Design\n\n描述性研究设计。\n",
            encoding="utf-8",
        )

    def test_question_driven_design_does_not_require_hypothesis_set(self) -> None:
        self._record_question_tree()
        self._write_design()

        result = record_design(
            self.root,
            {
                "slug": "descriptive-design",
                "title": "Descriptive design",
                "question_node_slug": "question-main",
                "target_estimand": "Population mean",
                "primary_outcome": "Measured outcome",
                "experimental_unit": "participant",
                "artifact_path": "designs/descriptive.md",
                "status": "draft",
                "feasibility_status": "unresolved",
                "feasibility_summary": "Awaiting execution resources.",
            },
        )

        self.assertIsNone(result["hypothesis_set_slug"])
        self.assertEqual(result["question_node_slug"], "question-main")
        design = list_designs(self.root)["designs"][0]
        self.assertIsNone(design["hypothesis_set_id"])
        self.assertEqual(design["question_node_slug"], "question-main")
        self.assertTrue(validate(self.root)["ok"])

    def test_research_tree_records_active_path_and_scientific_relation(self) -> None:
        self._record_question_tree()
        record_research_node(
            self.root,
            {
                "slug": "claim-a",
                "kind": "claim",
                "label": "Candidate claim",
                "parent_slug": "question-main",
            },
        )
        record_research_edge(
            self.root,
            {
                "source_slug": "claim-a",
                "relation": "supports",
                "target_slug": "question-main",
                "basis_type": "analysis",
                "basis_ref": "analysis:primary",
                "note": "Result is directionally consistent with the question.",
            },
        )

        tree = get_research_tree(self.root)
        self.assertEqual(tree["state"]["root_slug"], "objective-root")
        self.assertEqual(tree["state"]["active_slug"], "question-main")
        self.assertEqual(
            [item["slug"] for item in tree["active_path"]],
            ["objective-root", "question-main"],
        )
        self.assertEqual(tree["edges"][0]["relation"], "supports")
        self.assertTrue(research_tree_completion_readiness(self.root)["ready"])

        with self.assertRaisesRegex(ResearchDbError, "note 不可静默改写"):
            record_research_edge(
                self.root,
                {
                    "source_slug": "claim-a",
                    "relation": "supports",
                    "target_slug": "question-main",
                    "basis_type": "analysis",
                    "basis_ref": "analysis:primary",
                    "note": "Changed interpretation.",
                },
            )

    def test_study_records_execution_and_links_dataset(self) -> None:
        self._record_question_tree()
        self._write_design()
        record_design(
            self.root,
            {
                "slug": "execution-design",
                "title": "Execution design",
                "question_node_slug": "question-main",
                "target_estimand": "Population mean",
                "primary_outcome": "Measured outcome",
                "experimental_unit": "participant",
                "artifact_path": "designs/descriptive.md",
                "status": "frozen",
                "feasibility_status": "ready",
                "freeze_commit": "freeze-placeholder",
            },
        )

        (self.root / "study").mkdir(exist_ok=True)
        (self.root / "study" / "README.md").write_text(
            "# Study\n\n实际实施记录。\n",
            encoding="utf-8",
        )
        (self.root / "study" / "protocol.md").write_text(
            "# Protocol\n\n实际使用的测量流程。\n",
            encoding="utf-8",
        )
        now = datetime.now(timezone.utc)
        started = (now - timedelta(minutes=10)).isoformat()
        assay_started = (now - timedelta(minutes=5)).isoformat()

        bundle = {
            "slug": "study-1",
            "title": "Study 1",
            "design_slug": "execution-design",
            "study_type": "observational",
            "status": "completed",
            "provenance_path": "study/README.md",
            "started_at": started,
            "samples": [
                {
                    "sample_key": "sample-1",
                    "source_identity": "participant-1",
                    "experimental_unit_identity": "participant-1",
                    "sample_type": "biospecimen",
                    "status": "collected",
                    "metadata": {"visit": 1},
                }
            ],
            "assays": [
                {
                    "slug": "assay-1",
                    "assay_type": "measurement",
                    "measurement_target": "outcome",
                    "status": "completed",
                    "started_at": assay_started,
                    "sample_keys": ["sample-1"],
                }
            ],
            "deviations": [
                {
                    "deviation_key": "late-start",
                    "description": "Measurement started later than planned.",
                    "reason": "Instrument availability",
                    "affected_units": "sample-1",
                    "scientific_impact": "Timing deviation is retained for interpretation.",
                }
            ],
            "artifacts": [
                {
                    "role": "protocol",
                    "location": "study/protocol.md",
                    "storage_kind": "local",
                    "git_tracking": "required",
                }
            ],
        }

        first = record_study(self.root, bundle)
        second = record_study(self.root, bundle)
        self.assertEqual(first["study_id"], second["study_id"])
        studies = list_studies(self.root)["studies"]
        self.assertEqual(len(studies), 1)
        self.assertEqual(len(studies[0]["samples"]), 1)
        self.assertEqual(len(studies[0]["assays"]), 1)
        self.assertEqual(len(studies[0]["deviations"]), 1)
        self.assertTrue(study_completion_readiness(self.root)["ready"])

        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / "README.md").write_text("# Data\n", encoding="utf-8")
        (self.root / "data" / "raw.csv").write_text("id,value\n1,2\n", encoding="utf-8")
        dataset_bundle = {
            "slug": "dataset-1",
            "title": "Dataset 1",
            "source": "study execution",
            "received_at": now.isoformat(),
            "unit_of_inference": "participant",
            "provenance_path": "data/README.md",
            "study_slug": "study-1",
            "artifacts": [{"role": "raw", "location": "data/raw.csv"}],
        }
        record_dataset(self.root, dataset_bundle)
        dataset = list_datasets(self.root)["datasets"][0]
        self.assertEqual(dataset["study_id"], first["study_id"])

        dataset_bundle_without_repeat_link = dict(dataset_bundle)
        dataset_bundle_without_repeat_link.pop("study_slug")
        record_dataset(self.root, dataset_bundle_without_repeat_link)
        self.assertTrue(validate(self.root)["ok"])

    def test_planning_completion_accepts_frozen_question_driven_design(self) -> None:
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "research@example.test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Research Test"],
            check=True,
        )
        self._record_question_tree()
        self._write_design()
        subprocess.run(
            ["git", "-C", str(self.root), "add", "designs/descriptive.md"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "freeze descriptive design"],
            check=True,
            capture_output=True,
        )
        freeze_commit = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        record_design(
            self.root,
            {
                "slug": "descriptive-design",
                "title": "Descriptive design",
                "question_node_slug": "question-main",
                "target_estimand": "Population mean",
                "primary_outcome": "Measured outcome",
                "experimental_unit": "participant",
                "artifact_path": "designs/descriptive.md",
                "status": "frozen",
                "feasibility_status": "ready",
                "freeze_commit": freeze_commit,
            },
        )

        readiness = planning_completion_readiness(self.root)
        self.assertTrue(readiness["ready"], readiness["blockers"])
        self.assertEqual(readiness["hypothesis_set_count"], 0)
        self.assertEqual(readiness["frozen_design_count"], 1)


if __name__ == "__main__":
    unittest.main()
