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
    record_analysis_attempt,
    record_dataset,
)


class DownstreamResearchProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text(
            """# Research

## Objective

验证项目数据、确认性分析与结果溯源的完成门禁。

## Current Loop

ANALYSIS

## Active Uncertainty

预先指定分析能否在冻结输入和代码后产生可审计结果？

## Current State

当前测试按步骤登记数据集、分析、结果产物与项目观察。

## Active Work

继续取得并解释与预定义估计目标对应的分析证据。

## Open Threads

暂无当前优先处理的其他分析问题。

## Key Decisions

结果前计划与输入保持冻结，结果后信息只追加溯源记录。

## References

- `.research/research.sqlite`
""",
            encoding="utf-8",
        )
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
        (self.root / "scripts" / "analyses").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "analyses" / "trajectory.py").write_text(
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
                "code_path": "scripts/analyses/trajectory.py",
                "dataset_slugs": ["sleep-data"],
            },
        )

    def _select_attempt(self, git_commit: str, *, attempt_key: str = "A001") -> None:
        record_analysis_attempt(
            self.root,
            {
                "analysis_slug": "sleep-trajectory",
                "attempt_key": attempt_key,
                "status": "selected",
                "git_commit": git_commit,
                "reason": "Primary executable specification for this test.",
                "decision_reason": "This is the prespecified execution used for the reported result.",
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
        self._select_attempt(freeze_commit)

        outputs = self.root / "analysis" / "trajectory" / "outputs"
        outputs.mkdir()
        estimate_path = outputs / "primary.csv"
        diagnostic_path = outputs / "diagnostic.txt"
        estimate_path.write_text("term,estimate,low,high\nslope,11.4,7.8,15.1\n", encoding="utf-8")
        diagnostic_path.write_text("converged=true\n", encoding="utf-8")
        completed_at = list_analyses(self.root)["analyses"][0]["started_at"]

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
                "code_path": "scripts/analyses/trajectory.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "completed_at": completed_at,
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
        self.assertIn("scripts/analyses/trajectory.py", canonical)
        self.assertIn("analysis/trajectory/outputs/primary.csv", canonical)

    def test_post_result_dataset_provenance_can_remain_canonical_without_joining_freeze(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")
        self._select_attempt(freeze_commit)

        provenance_path = self.root / "data" / "sleep" / "post-result-provenance.md"
        provenance_path.write_text(
            "# 后验来源核验\n\n结果可见后补充的来源与测量语义核验。\n",
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
                    {
                        "role": "metadata",
                        "location": "data/sleep/post-result-provenance.md",
                    },
                ],
            },
        )

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
                "code_path": "scripts/analyses/trajectory.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "dataset_artifact_timing": [
                    {
                        "dataset_slug": "sleep-data",
                        "location": "data/sleep/post-result-provenance.md",
                        "timing_role": "post_result_context",
                        "reason": "Source provenance was added only after the primary result was visible.",
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
        self._commit("RESEARCH: add result and post-result provenance")

        result = validate_completion(self.root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertIn(
            "data/sleep/post-result-provenance.md",
            set(result["git"]["canonical_paths"]),
        )

    def test_post_result_context_must_actually_postdate_the_analysis_freeze(self) -> None:
        self._write_plan_assets()
        provenance_path = self.root / "data" / "sleep" / "preexisting-provenance.md"
        provenance_path.write_text(
            "# 既有来源核验\n\n该文件在结果前已经存在。\n", encoding="utf-8"
        )
        self._record_dataset()
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
                    {
                        "role": "metadata",
                        "location": "data/sleep/preexisting-provenance.md",
                    },
                ],
            },
        )
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze plan with provenance already present")

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
                "code_path": "scripts/analyses/trajectory.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": freeze_commit,
                "dataset_artifact_timing": [
                    {
                        "dataset_slug": "sleep-data",
                        "location": "data/sleep/preexisting-provenance.md",
                        "timing_role": "post_result_context",
                        "reason": "Incorrectly claimed to be post-result context.",
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
        self._commit("ANALYSIS: record result with invalid context timing")

        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = [
            item
            for item in result["downstream"]["blockers"]
            if item["reason"] == "analysis_post_result_context_present_at_freeze"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["paths"], ["data/sleep/preexisting-provenance.md"])

    def test_post_result_context_scope_is_specific_to_each_analysis(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        first_freeze = self._commit("ANALYSIS: freeze first plan")

        provenance_path = self.root / "data" / "sleep" / "post-result-provenance.md"
        provenance_path.write_text(
            "# 后验来源核验\n\n第一轮结果后补充。\n", encoding="utf-8"
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
                    {
                        "role": "metadata",
                        "location": "data/sleep/post-result-provenance.md",
                    },
                ],
            },
        )
        first_outputs = self.root / "analysis" / "trajectory" / "outputs"
        first_outputs.mkdir()
        (first_outputs / "primary.csv").write_text("term,estimate\nslope,11.4\n", encoding="utf-8")
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
                "code_path": "scripts/analyses/trajectory.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": first_freeze,
                "dataset_artifact_timing": [
                    {
                        "dataset_slug": "sleep-data",
                        "location": "data/sleep/post-result-provenance.md",
                        "timing_role": "post_result_context",
                        "reason": "Added after the first analysis result became visible.",
                    }
                ],
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "First result exists.",
                        "source_path": "analysis/trajectory/outputs/primary.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record first result and later provenance")

        second_dir = self.root / "analysis" / "trajectory-second"
        second_dir.mkdir()
        (second_dir / "README.md").write_text(
            "# 第二轮分析计划\n\n此时后验来源核验已成为既有上下文。\n", encoding="utf-8"
        )
        (self.root / "scripts" / "analyses" / "trajectory-second.py").write_text(
            "print('second analysis')\n", encoding="utf-8"
        )
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory-second",
                "title": "Second sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "planned",
                "target_uncertainty": "Does the updated analysis remain positive?",
                "estimand": "Population-average change per study day in the second analysis",
                "unit_of_inference": "participant",
                "primary_analysis": "Second prespecified mixed model",
                "analysis_path": "analysis/trajectory-second/README.md",
                "code_path": "scripts/analyses/trajectory-second.py",
                "dataset_slugs": ["sleep-data"],
            },
        )
        second_freeze = self._commit("ANALYSIS: freeze second plan")

        provenance_path.write_text(
            "# 后验来源核验\n\n第二轮 freeze 后被覆盖，这是不允许的。\n", encoding="utf-8"
        )
        second_outputs = second_dir / "outputs"
        second_outputs.mkdir()
        (second_outputs / "primary.csv").write_text("term,estimate\nslope,10.1\n", encoding="utf-8")
        record_analysis(
            self.root,
            {
                "slug": "sleep-trajectory-second",
                "title": "Second sleep trajectory analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": "Does the updated analysis remain positive?",
                "estimand": "Population-average change per study day in the second analysis",
                "unit_of_inference": "participant",
                "primary_analysis": "Second prespecified mixed model",
                "analysis_path": "analysis/trajectory-second/README.md",
                "code_path": "scripts/analyses/trajectory-second.py",
                "dataset_slugs": ["sleep-data"],
                "freeze_commit": second_freeze,
                "artifacts": [
                    {"role": "estimate", "path": "analysis/trajectory-second/outputs/primary.csv"}
                ],
                "observations": [
                    {
                        "statement": "Second result exists.",
                        "source_path": "analysis/trajectory-second/outputs/primary.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record second result after mutating frozen context")

        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = [
            item
            for item in result["downstream"]["blockers"]
            if item["reason"] == "analysis_frozen_artifact_changed_after_freeze"
            and item["analysis"] == "sleep-trajectory-second"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertIn("data/sleep/post-result-provenance.md", blockers[0]["paths"])

    def test_completion_rejects_committed_changes_to_frozen_code_and_input(self) -> None:
        self._write_plan_assets()
        self._record_dataset()
        self._record_planned_analysis()
        freeze_commit = self._commit("ANALYSIS: freeze primary plan")

        (self.root / "data" / "sleep" / "raw.csv").write_text(
            "subject,day,y\n1,0,10\n1,1,99\n", encoding="utf-8"
        )
        (self.root / "scripts" / "analyses" / "trajectory.py").write_text(
            "print('changed after results were visible')\n", encoding="utf-8"
        )
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
                "code_path": "scripts/analyses/trajectory.py",
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
        self._commit("ANALYSIS: commit changed frozen inputs")

        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = [
            item
            for item in result["downstream"]["blockers"]
            if item["reason"] == "analysis_frozen_artifact_changed_after_freeze"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(
            set(blockers[0]["paths"]),
            {"data/sleep/raw.csv", "scripts/analyses/trajectory.py"},
        )

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
                "code_path": "scripts/analyses/trajectory.py",
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
                "code_path": "scripts/analyses/trajectory.py",
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
                    "code_path": "scripts/analyses/trajectory.py",
                    "dataset_slugs": ["sleep-data"],
                    "freeze_commit": freeze_commit,
                },
            )


if __name__ == "__main__":
    unittest.main()
