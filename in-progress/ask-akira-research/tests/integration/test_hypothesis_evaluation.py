from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime, timedelta
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, init_database  # noqa: E402
from research_db_ops.completion import validate_completion  # noqa: E402
from research_db_ops.downstream import record_analysis, record_dataset  # noqa: E402
from research_db_ops.planning import (  # noqa: E402
    record_design,
    record_hypothesis_evaluation,
    record_hypothesis_proposal,
    record_hypothesis_set,
)


class HypothesisEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "hypotheses").mkdir(parents=True)
        (self.root / "designs").mkdir(parents=True)
        (self.root / "data" / "trial").mkdir(parents=True)
        (self.root / "analysis" / "primary").mkdir(parents=True)
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "RESEARCH.md").write_text(
            """# Research

## Objective

比较两个随机处理的平均结局差异。

## Current Loop

QUESTION

## Active Uncertainty

A 相对 B 的平均处理效应属于哪个预定义效应区域？

## Current State

结果前假设、设计、数据与分析溯源按测试步骤逐步登记。

## Active Work

继续取得能够区分预定义效应区域的证据。

## Open Threads

暂无当前优先处理的其他问题。

## Key Decisions

保持结果前冻结与结果后评价分离。

## References

- `.research/research.sqlite`
""",
            encoding="utf-8",
        )
        (self.root / "hypotheses" / "treatment-effect.md").write_text(
            "# 假设集合\n\n比较正向、较小和负向处理效应。\n",
            encoding="utf-8",
        )
        (self.root / "designs" / "treatment-effect.md").write_text(
            "# 研究设计\n\n主要估计目标为 A 相对 B 的平均处理效应。\n",
            encoding="utf-8",
        )
        (self.root / "data" / "trial" / "README.md").write_text(
            "# 数据来源\n\n个体是独立实验单位。\n", encoding="utf-8"
        )
        (self.root / "data" / "trial" / "raw.csv").write_text(
            "subject,treatment,y\n1,A,10\n2,B,9\n", encoding="utf-8"
        )
        (self.root / "analysis" / "primary" / "README.md").write_text(
            "# 分析计划\n\n主要比较 A-B 平均差。\n", encoding="utf-8"
        )
        (self.root / "analysis" / "primary" / "run.py").write_text(
            "print('analysis')\n", encoding="utf-8"
        )
        (self.root / "scripts" / "support.py").write_text(
            "print('support diagnostics')\n", encoding="utf-8"
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

    def _record_planning_and_dataset(self) -> tuple[str, str]:
        scientific_freeze = self._commit("RESEARCH: freeze question and design")
        uncertainty = "A 相对 B 的平均处理效应属于哪个预定义效应区域？"
        estimand = "E[Y(A)-Y(B)]"
        record_hypothesis_proposal(
            self.root,
            {
                "slug": "treatment-effect-regions",
                "origin": "agent",
                "original_statement": "处理效应可能落在预定义的不同效应区域。",
                "rationale": "该 proposal 将当前 Active Uncertainty 操作化为可由预定义边界判别的竞争状态。",
            },
        )
        record_hypothesis_set(
            self.root,
            {
                "slug": "treatment-effect",
                "title": "Treatment effect hypothesis set",
                "target_uncertainty": uncertainty,
                "artifact_path": "hypotheses/treatment-effect.md",
                "status": "frozen",
                "freeze_commit": scientific_freeze,
                "proposal_slugs": ["treatment-effect-regions"],
            },
        )
        record_design(
            self.root,
            {
                "slug": "treatment-effect",
                "title": "Treatment effect design",
                "hypothesis_set_slug": "treatment-effect",
                "target_estimand": estimand,
                "primary_outcome": "individual outcome",
                "experimental_unit": "individual",
                "artifact_path": "designs/treatment-effect.md",
                "status": "frozen",
                "feasibility_status": "ready",
                "freeze_commit": scientific_freeze,
            },
        )
        record_dataset(
            self.root,
            {
                "slug": "trial-data",
                "title": "Trial data",
                "identity": "test:trial:v1",
                "source": "test fixture",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "individual",
                "provenance_path": "data/trial/README.md",
                "artifacts": [{"role": "raw", "location": "data/trial/raw.csv"}],
            },
        )
        return uncertainty, estimand

    def test_matching_confirmatory_analysis_requires_explicit_design_link(self) -> None:
        uncertainty, estimand = self._record_planning_and_dataset()
        with self.assertRaisesRegex(ResearchDbError, "必须显式提供 design_slug"):
            record_analysis(
                self.root,
                {
                    "slug": "primary",
                    "title": "Primary analysis",
                    "analysis_mode": "confirmatory",
                    "status": "planned",
                    "target_uncertainty": uncertainty,
                    "estimand": estimand,
                    "unit_of_inference": "individual",
                    "primary_analysis": "Welch mean difference",
                    "analysis_path": "analysis/primary/README.md",
                    "code_path": "analysis/primary/run.py",
                    "dataset_slugs": ["trial-data"],
                },
            )

    def test_completed_linked_analysis_requires_hypothesis_evaluation(self) -> None:
        uncertainty, estimand = self._record_planning_and_dataset()
        record_analysis(
            self.root,
            {
                "slug": "primary",
                "title": "Primary analysis",
                "analysis_mode": "confirmatory",
                "status": "planned",
                "target_uncertainty": uncertainty,
                "estimand": estimand,
                "unit_of_inference": "individual",
                "primary_analysis": "Welch mean difference",
                "analysis_path": "analysis/primary/README.md",
                "code_path": "analysis/primary/run.py",
                "dataset_slugs": ["trial-data"],
                "design_slug": "treatment-effect",
                "artifacts": [
                    {
                        "role": "other",
                        "path": "scripts/support.py",
                        "timing_role": "pre_result_support",
                    }
                ],
            },
        )
        analysis_freeze = self._commit("ANALYSIS: freeze input and plan")
        result_path = self.root / "analysis" / "primary" / "result.csv"
        result_path.write_text("estimate,low,high\n1,-5,7\n", encoding="utf-8")
        record_analysis(
            self.root,
            {
                "slug": "primary",
                "title": "Primary analysis",
                "analysis_mode": "confirmatory",
                "status": "completed",
                "target_uncertainty": uncertainty,
                "estimand": estimand,
                "unit_of_inference": "individual",
                "primary_analysis": "Welch mean difference",
                "analysis_path": "analysis/primary/README.md",
                "code_path": "analysis/primary/run.py",
                "dataset_slugs": ["trial-data"],
                "design_slug": "treatment-effect",
                "freeze_commit": analysis_freeze,
                "artifacts": [
                    {"role": "estimate", "path": "analysis/primary/result.csv"}
                ],
                "observations": [
                    {
                        "statement": "区间仍跨越多个预定义效应区域。",
                        "source_path": "analysis/primary/result.csv",
                    }
                ],
            },
        )
        self._commit("ANALYSIS: record result")

        before = validate_completion(self.root)
        reasons = {item["reason"] for item in before["planning"]["blockers"]}
        self.assertIn("completed_confirmatory_analysis_missing_hypothesis_evaluation", reasons)

        with sqlite3.connect(self.root / ".research" / "research.sqlite") as connection:
            completed_at = connection.execute(
                "SELECT completed_at FROM analysis_runs WHERE slug = 'primary'"
            ).fetchone()[0]
        premature_evaluation = (
            datetime.fromisoformat(completed_at) - timedelta(seconds=1)
        ).isoformat()

        with self.assertRaisesRegex(ResearchDbError, "不能早于.*completed_at"):
            record_hypothesis_evaluation(
                self.root,
                {
                    "hypothesis_set_slug": "treatment-effect",
                    "analysis_slug": "primary",
                    "resolution_status": "unresolved",
                    "decision": "premature evaluation",
                    "summary": "该评价时间早于 Analysis 完成时间，必须拒绝。",
                    "source_path": "analysis/primary/result.csv",
                    "evaluated_at": premature_evaluation,
                },
            )

        record_hypothesis_evaluation(
            self.root,
            {
                "hypothesis_set_slug": "treatment-effect",
                "analysis_slug": "primary",
                "resolution_status": "unresolved",
                "decision": "inconclusive",
                "summary": "主要区间跨越多个预定义效应区域，因此本轮证据不足以区分竞争假设。",
                "source_path": "analysis/primary/result.csv",
            },
        )
        self._commit("INTERPRETATION: record hypothesis evaluation")
        after = validate_completion(self.root)
        self.assertTrue(after["ok"], after["errors"])
        self.assertEqual(after["planning"]["hypothesis_evaluation_count"], 1)

        with self.assertRaisesRegex(ResearchDbError, "不可覆盖"):
            record_hypothesis_evaluation(
                self.root,
                {
                    "hypothesis_set_slug": "treatment-effect",
                    "analysis_slug": "primary",
                    "resolution_status": "resolved",
                    "decision": "changed after seeing result",
                    "summary": "This second evaluation must not overwrite the first event.",
                    "source_path": "analysis/primary/result.csv",
                },
            )

        with sqlite3.connect(self.root / ".research" / "research.sqlite") as connection:
            connection.execute(
                "UPDATE hypothesis_evaluations SET evaluated_at = ? WHERE analysis_id = 1",
                (premature_evaluation,),
            )
        self._commit("TEST: persist invalid evaluation chronology")
        invalid = validate_completion(self.root)
        reasons = {item["reason"] for item in invalid["planning"]["blockers"]}
        self.assertIn("hypothesis_evaluation_before_analysis_completion", reasons)

    def test_dataset_can_append_provenance_artifact_without_changing_identity(self) -> None:
        self._record_planning_and_dataset()
        transform = self.root / "scripts"
        (transform / "curate.py").write_text("print('curate')\n", encoding="utf-8")
        record_dataset(
            self.root,
            {
                "slug": "trial-data",
                "title": "Trial data",
                "identity": "test:trial:v1",
                "source": "test fixture",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "individual",
                "provenance_path": "data/trial/README.md",
                "artifacts": [{"role": "other", "location": "scripts/curate.py"}],
            },
        )
        result = validate_completion(self.root)
        self.assertIn("scripts/curate.py", set(result["git"]["canonical_paths"]))

        with self.assertRaisesRegex(ResearchDbError, "不能.*静默修改"):
            record_dataset(
                self.root,
                {
                    "slug": "trial-data",
                    "title": "Mutated dataset identity",
                    "identity": "test:trial:v1",
                    "source": "test fixture",
                    "received_at": "2026-08-28T00:00:00+00:00",
                    "unit_of_inference": "individual",
                    "provenance_path": "data/trial/README.md",
                    "artifacts": [{"role": "other", "location": "scripts/curate.py"}],
                },
            )


if __name__ == "__main__":
    unittest.main()
