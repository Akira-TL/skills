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
from research_db_ops.downstream import record_analysis, record_dataset  # noqa: E402


class DownstreamResearchProvenanceTests(unittest.TestCase):
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

    def test_completion_rejects_tracked_downstream_files_without_database_records(self) -> None:
        self._write_plan_assets()
        self._commit("RESEARCH: add unregistered downstream assets")
        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        reasons = {item["reason"] for item in result["downstream"]["blockers"]}
        self.assertIn("tracked_downstream_artifacts_unregistered", reasons)
        self.assertIn("data_assets_present_without_dataset_record", reasons)
        self.assertIn("analysis_assets_present_without_analysis_record", reasons)

    def test_completed_confirmatory_analysis_freezes_plan_and_tracks_results(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        estimate_path = outputs / "primary.csv"
        diagnostic_path = outputs / "diagnostic.txt"
        estimate_path.write_text("term,estimate,low,high\nslope,11.4,7.8,15.1\n", encoding="utf-8")
        diagnostic_path.write_text("converged=true\n", encoding="utf-8")

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
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"},
                    {"role": "diagnostic", "path": "analysis/trajectory/outputs/diagnostic.txt"},
                ],
                "amendments": [
                    {
                        "timing": "post_result",
                        "description": "Inspect an extreme residual without replacing the primary estimand.",
                        "reason": "Primary diagnostics exposed a large residual.",
                    }
                ],
                "observations": [
                    {
                        "statement": "The estimated population-average slope was positive.",
                        "effect": "+11.4 units/day",
                        "statistics": {"estimate": 11.4, "ci_low": 7.8, "ci_high": 15.1},
                        "scope": "Current repeated-measures dataset",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                        "source_locator": "row slope",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record primary result")

        result = validate_completion(self.root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(result["downstream"]["ready"])
        canonical = set(result["git"]["canonical_paths"])
        self.assertIn("data/sleep/raw.csv", canonical)
        self.assertIn("analysis/trajectory/run.py", canonical)
        self.assertIn("analysis/trajectory/outputs/primary.csv", canonical)

    def test_result_artifact_cannot_exist_in_declared_pre_result_freeze(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        estimate_path = outputs / "primary.csv"
        estimate_path.write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
        freeze_commit = self._commit("ANALYSIS: invalid freeze already containing results")

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
        self._commit("ANALYSIS: register invalid freeze provenance")
        result = validate_completion(self.root)
        reasons = {item["reason"] for item in result["downstream"]["blockers"]}
        self.assertIn("analysis_result_artifact_present_at_freeze", reasons)

    def test_frozen_analysis_cannot_silently_change_estimand(self) -> None:
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
        with self.assertRaisesRegex(ResearchDbError, "不能静默修改"):
            record_analysis(
                self.root,
                {
                    "slug": "sleep-trajectory",
                    "title": "Sleep trajectory analysis",
                    "analysis_mode": "confirmatory",
                    "status": "frozen",
                    "target_uncertainty": "Is there a stable positive longitudinal trend?",
                    "estimand": "Post-hoc maximum day contrast",
                    "unit_of_inference": "participant",
                    "primary_analysis": "Mixed model with participant random intercept and slope",
                    "analysis_path": "analysis/trajectory/README.md",
                    "code_path": "analysis/trajectory/run.py",
                    "dataset_slugs": ["sleep-data"],
                    "freeze_commit": freeze_commit,
                },
            )


if __name__ == "__main__":
    unittest.main()
