from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, init_database  # noqa: E402
from research_db_ops.completion import validate_completion  # noqa: E402
from research_db_ops.downstream import (  # noqa: E402
    list_analyses,
    record_analysis,
    record_dataset,
)


class AnalysisFreezeHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n\n中文科研状态。\n", encoding="utf-8")
        init_database(self.root)
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "research@example.test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Research Test"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_plan_assets(self) -> None:
        (self.root / "data" / "sleep").mkdir(parents=True)
        (self.root / "analysis" / "trajectory").mkdir(parents=True)
        (self.root / "data" / "sleep" / "README.md").write_text(
            "# 数据来源\n\n受试者是独立推断单位。\n", encoding="utf-8"
        )
        (self.root / "data" / "sleep" / "raw.csv").write_text(
            "subject,day,y\n1,0,10\n1,1,12\n", encoding="utf-8"
        )
        (self.root / "analysis" / "trajectory" / "README.md").write_text(
            "# 分析计划\n\n主要估计量为每日变化斜率。\n", encoding="utf-8"
        )
        (self.root / "analysis" / "trajectory" / "run.py").write_text(
            "print('analysis')\n", encoding="utf-8"
        )

    def _record_dataset(self) -> None:
        record_dataset(
            self.root,
            {
                "slug": "sleep-data",
                "title": "Sleep repeated measures",
                "identity": "example:sleep",
                "source": "test fixture",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "participant",
                "provenance_path": "data/sleep/README.md",
                "artifacts": [
                    {
                        "role": "raw",
                        "location": "data/sleep/raw.csv",
                    }
                ],
            },
        )

    def _record_planned_analysis(self) -> None:
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "planned",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
            },
        )

    def _commit(self, message: str) -> str:
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", message],
            check=True,
            capture_output=True,
        )
        return subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()

    def test_post_result_context_cannot_predate_first_result_artifact(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        provenance_path = self.root / "data" / "sleep" / "premature-context.md"
        provenance_path.write_text(
            "# 来源核验\n\n该文件晚于 freeze，但早于首次结果 artifact。\n",
            encoding="utf-8",
        )
        record_dataset(
            self.root,
            {
                "slug": "sleep-data",
                "title": "Sleep repeated measures",
                "identity": "example:sleep",
                "source": "test fixture",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "participant",
                "provenance_path": "data/sleep/README.md",
                "artifacts": [
                    {"role": "raw", "location": "data/sleep/raw.csv"},
                    {"role": "metadata", "location": "data/sleep/premature-context.md"},
                ],
            },
        )
        self._commit("DATA: add context before result artifact")

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        (outputs / "primary.csv").write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "dataset_artifact_timing": [
                    {
                        "dataset_slug": "sleep-data",
                        "location": "data/sleep/premature-context.md",
                        "timing_role": "post_result_context",
                        "reason": "Incorrectly labeled as if it followed result visibility.",
                    }
                ],
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "A result exists.",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record result after premature context")

        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = [
            item
            for item in result["downstream"]["blockers"]
            if item["reason"] == "analysis_post_result_context_predates_results"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["paths"], ["data/sleep/premature-context.md"])

    def test_completion_rejects_reverted_history_changes_to_frozen_input(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        raw_path = self.root / "data" / "sleep" / "raw.csv"
        original = raw_path.read_text(encoding="utf-8")
        raw_path.write_text("subject,day,y\n1,0,10\n1,1,99\n", encoding="utf-8")
        self._commit("ANALYSIS: mutate frozen input")
        raw_path.write_text(original, encoding="utf-8")
        self._commit("ANALYSIS: revert frozen input content")

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        estimate_path = outputs / "primary.csv"
        estimate_path.write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "A result exists.",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record result after reverted input history")

        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = [
            item
            for item in result["downstream"]["blockers"]
            if item["reason"] == "analysis_frozen_artifact_changed_after_freeze"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["paths"], ["data/sleep/raw.csv"])

    def test_completed_analysis_preserves_completed_at_when_appending_provenance(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        (outputs / "primary.csv").write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
        completed_at = "2026-08-28T01:00:00+00:00"
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "completed_at": completed_at,
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "A result exists.",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record primary result")

        context_path = self.root / "data" / "sleep" / "post-result-context.md"
        context_path.write_text("# 后验来源核验\n\n结果后补充。\n", encoding="utf-8")
        record_dataset(
            self.root,
            {
                "slug": "sleep-data",
                "title": "Sleep repeated measures",
                "identity": "example:sleep",
                "source": "test fixture",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "participant",
                "provenance_path": "data/sleep/README.md",
                "artifacts": [
                    {"role": "raw", "location": "data/sleep/raw.csv"},
                    {"role": "metadata", "location": "data/sleep/post-result-context.md"},
                ],
            },
        )
        self._commit("DATA: add post-result context")

        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "dataset_artifact_timing": [
                    {
                        "dataset_slug": "sleep-data",
                        "location": "data/sleep/post-result-context.md",
                        "timing_role": "post_result_context",
                        "reason": "Source context was added after the result artifact was committed.",
                    }
                ],
            },
        )

        analysis = list_analyses(self.root)["analyses"][0]
        self.assertEqual(analysis["completed_at"], completed_at)

    def test_completed_analysis_cannot_silently_change_completed_at(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        (outputs / "primary.csv").write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "completed_at": "2026-08-28T01:00:00+00:00",
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "A result exists.",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                    }
                ],
            },
        )

        with self.assertRaisesRegex(ResearchDbError, "completed_at"):
            record_analysis(
                self.root,
                {
                    "slug": "sleep-trajectory",
                    "title": "Sleep trajectory analysis",
                    "analysis_mode": "confirmatory",
                    "status": "completed",
                    "target_uncertainty": "Is there a stable positive longitudinal trend?",
                    "estimand": "Population-average change per study day",
                    "unit_of_inference": "participant",
                    "primary_analysis": "Mixed model with participant random intercept and slope",
                    "analysis_path": "analysis/trajectory/README.md",
                    "code_path": "analysis/trajectory/run.py",
                    "dataset_slugs": ["sleep-data"],
                    "freeze_commit": freeze_commit,
                    "completed_at": "2026-08-29T01:00:00+00:00",
                },
            )

    def test_frozen_analysis_cannot_silently_change_freeze_commit(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory",
                "title": "Sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "frozen",
                "target_uncertainty": "Is there a stable positive longitudinal trend?",
                "estimand": "Population-average change per study day",
                "unit_of_inference": "participant",
                "primary_analysis": "Mixed model with participant random intercept and slope",
                "analysis_path": "analysis/trajectory/README.md",
                "code_path": "analysis/trajectory/run.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
            },
        )
        later_commit = self._commit("CHORE: persist frozen analysis record")

        with self.assertRaisesRegex(ResearchDbError, "不能静默修改"):
            record_analysis(
                self.root,
                {
                    "slug": "sleep-trajectory",
                    "title": "Sleep trajectory analysis",
                    "analysis_mode": "confirmatory",
                    "status": "frozen",
                    "target_uncertainty": "Is there a stable positive longitudinal trend?",
                    "estimand": "Population-average change per study day",
                    "unit_of_inference": "participant",
                    "primary_analysis": "Mixed model with participant random intercept and slope",
                    "analysis_path": "analysis/trajectory/README.md",
                    "code_path": "analysis/trajectory/run.py",
                    "dataset_slugs": ["sleep-data"],
                    "freeze_commit": later_commit,
                },
            )


if __name__ == "__main__":
    unittest.main()
