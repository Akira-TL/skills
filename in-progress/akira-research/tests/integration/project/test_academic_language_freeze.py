from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import database_path, init_database  # noqa: E402
from research_db_ops.completion import academic_language_readiness  # noqa: E402
from research_db_ops.downstream import record_analysis, record_dataset  # noqa: E402
from research_db_support.storage import ResearchDbError  # noqa: E402


RESEARCH_MD = """# Research

## Objective

验证冻结前学术语言门禁不会把外部软件文档误判成人类科研正文。

## Current Loop

ANALYSIS

## Active Uncertainty

当前分析计划是否满足结果前冻结要求？

## Current State

当前仅建立测试输入和分析计划。

## Active Work

检查分析计划和软件文档证据的语言边界。

## Open Threads

暂无其他开放问题。

## Key Decisions

人类科研正文使用规范中文，外部软件文档保留原文。

## References

- `.research/research.sqlite`
"""


class AcademicLanguageFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text(RESEARCH_MD, encoding="utf-8")
        init_database(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_academic_language_ignores_analysis_machine_log_artifacts(self) -> None:
        analysis_dir = self.root / "analysis" / "example"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "README.md").write_text(
            "# 分析说明\n\n该文件使用中文记录研究问题、估计目标和证据边界。\n",
            encoding="utf-8",
        )
        software_contract = analysis_dir / "software_contract.txt"
        software_contract.write_text(
            "This is verbatim official software documentation retained as execution evidence. "
            "Parameters describe the public API, defaults, return values, constraints, examples, "
            "random sampling behavior, array shapes, replacement rules, and implementation notes. "
            "The text is not human-authored scientific interpretation and must remain unchanged.\n",
            encoding="utf-8",
        )
        now = "2026-09-04T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO analysis_runs(
                    slug, title, analysis_mode, status, target_uncertainty, estimand,
                    unit_of_inference, primary_analysis, analysis_path, code_path,
                    started_at, created_at, updated_at
                ) VALUES (
                    'example-log', '示例分析', 'exploratory', 'planned', '测试问题', '测试估计量',
                    'sample', '测试分析', 'analysis/example/README.md',
                    'analysis/example/README.md', ?, ?, ?
                )
                """,
                (now, now, now),
            )
            connection.execute(
                """
                INSERT INTO analysis_artifacts(
                    analysis_id, role, path, git_tracking, created_at, timing_role
                ) VALUES (?, 'log', 'analysis/example/software_contract.txt', 'required', ?, 'pre_result_support')
                """,
                (int(cursor.lastrowid), now),
            )

        result = academic_language_readiness(self.root)
        self.assertTrue(result["ready"], result["blockers"])

    def _record_language_dataset(self) -> None:
        data_dir = self.root / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "README.md").write_text("# 数据\n\n输入数据来源已经记录。\n", encoding="utf-8")
        (data_dir / "raw.csv").write_text("id,value\n1,2\n", encoding="utf-8")
        record_dataset(
            self.root,
            {
                "slug": "dataset-language",
                "title": "语言测试数据集",
                "source": "test fixture",
                "received_at": "2026-09-04T00:00:00+00:00",
                "unit_of_inference": "sample",
                "provenance_path": "data/README.md",
                "artifacts": [{"role": "raw", "location": "data/raw.csv"}],
            },
        )

    def test_exploratory_analysis_requires_planned_preflight_before_completion(self) -> None:
        self._record_language_dataset()
        analysis_dir = self.root / "analysis" / "exploratory-language"
        analysis_dir.mkdir(parents=True)
        plan = analysis_dir / "README.md"
        plan.write_text(
            "# 探索性分析计划\n\n当前 exploratory analysis 使用 randomization 检查候选模式。\n",
            encoding="utf-8",
        )
        (analysis_dir / "run.py").write_text("print('ok')\n", encoding="utf-8")
        bundle = {
            "slug": "exploratory-language",
            "title": "探索性语言测试",
            "analysis_mode": "exploratory",
            "status": "planned",
            "target_uncertainty": "当前数据中是否存在值得继续检验的候选模式",
            "estimand": "候选模式的描述性差异",
            "unit_of_inference": "sample",
            "primary_analysis": "描述性探索与预先说明的诊断",
            "analysis_path": "analysis/exploratory-language/README.md",
            "code_path": "analysis/exploratory-language/run.py",
            "dataset_slugs": ["dataset-language"],
        }

        with self.assertRaisesRegex(ResearchDbError, "执行前学术语言检查失败"):
            record_analysis(self.root, bundle)

        with closing(sqlite3.connect(database_path(self.root))) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM analysis_runs WHERE slug = 'exploratory-language'"
                ).fetchone()[0],
                0,
            )

        plan.write_text(
            "# 探索性分析计划\n\n当前探索性分析使用固定的随机化检查评估候选模式。\n",
            encoding="utf-8",
        )
        result = record_analysis(self.root, bundle)
        self.assertEqual(result["status"], "planned")

        completed = dict(bundle)
        completed["status"] = "completed"
        result = record_analysis(self.root, completed)
        self.assertEqual(result["status"], "completed")

    def test_exploratory_analysis_cannot_first_register_as_completed(self) -> None:
        self._record_language_dataset()
        analysis_dir = self.root / "analysis" / "direct-completion"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "README.md").write_text(
            "# 探索性分析计划\n\n当前探索性分析用于评估候选模式。\n",
            encoding="utf-8",
        )
        (analysis_dir / "run.py").write_text("print('ok')\n", encoding="utf-8")

        with self.assertRaisesRegex(ResearchDbError, "第一次登记必须使用 status=planned"):
            record_analysis(
                self.root,
                {
                    "slug": "direct-completion",
                    "title": "直接完成测试",
                    "analysis_mode": "exploratory",
                    "status": "completed",
                    "target_uncertainty": "候选模式是否存在",
                    "estimand": "候选模式的描述性差异",
                    "unit_of_inference": "sample",
                    "primary_analysis": "描述性探索",
                    "analysis_path": "analysis/direct-completion/README.md",
                    "code_path": "analysis/direct-completion/run.py",
                    "dataset_slugs": ["dataset-language"],
                },
            )

    def test_analysis_preflight_checks_dataset_provenance(self) -> None:
        self._record_language_dataset()
        (self.root / "data" / "README.md").write_text(
            "# 数据\n\n当前 Dataset provenance 已记录，但仍含需要修正的裸英文科研术语。\n",
            encoding="utf-8",
        )
        analysis_dir = self.root / "analysis" / "dataset-provenance"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "README.md").write_text(
            "# 分析计划\n\n当前确认性分析使用固定规则评估主要差异。\n",
            encoding="utf-8",
        )
        (analysis_dir / "run.py").write_text("print('ok')\n", encoding="utf-8")

        with self.assertRaisesRegex(ResearchDbError, "data/README.md"):
            record_analysis(
                self.root,
                {
                    "slug": "dataset-provenance",
                    "title": "数据来源语言检查",
                    "analysis_mode": "confirmatory",
                    "status": "frozen",
                    "target_uncertainty": "主要差异是否存在",
                    "estimand": "主要差异",
                    "unit_of_inference": "sample",
                    "primary_analysis": "固定规则",
                    "analysis_path": "analysis/dataset-provenance/README.md",
                    "code_path": "analysis/dataset-provenance/run.py",
                    "freeze_commit": "freeze-placeholder",
                    "dataset_slugs": ["dataset-language"],
                },
            )

    def test_analysis_preflight_checks_linked_study_provenance(self) -> None:
        self._record_language_dataset()
        study_dir = self.root / "study"
        study_dir.mkdir()
        (study_dir / "EXECUTION_REPORT.md").write_text(
            "# 实施记录\n\n该 Study 已完成，但当前 Dataset 描述仍含需要修正的裸英文科研术语。\n",
            encoding="utf-8",
        )
        now = "2026-09-04T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                """
                INSERT INTO research_nodes(
                    slug, kind, label, workflow_status, branch_priority, created_at, updated_at
                ) VALUES ('study-language-q', 'question', '测试问题', 'active', 'primary', ?, ?)
                """,
                (now, now),
            )
            question_id = int(cursor.lastrowid)
            cursor = connection.execute(
                """
                INSERT INTO research_designs(
                    slug, title, question_node_id, target_estimand, primary_outcome,
                    experimental_unit, artifact_path, status, feasibility_status,
                    feasibility_summary, freeze_commit, created_at, updated_at
                ) VALUES (
                    'study-language-design', '测试设计', ?, '主要差异', '主要结局',
                    'sample', 'designs/test.md', 'frozen', 'ready',
                    '测试环境可执行。', 'freeze-placeholder', ?, ?
                )
                """,
                (question_id, now, now),
            )
            design_id = int(cursor.lastrowid)
            cursor = connection.execute(
                """
                INSERT INTO studies(
                    slug, title, design_id, study_type, status, provenance_path,
                    started_at, completed_at, created_at, updated_at
                ) VALUES (
                    'study-language', '测试实施', ?, '合成研究', 'completed',
                    'study/EXECUTION_REPORT.md', ?, ?, ?, ?
                )
                """,
                (design_id, now, now, now, now),
            )
            study_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE datasets SET study_id = ? WHERE slug = 'dataset-language'",
                (study_id,),
            )

        analysis_dir = self.root / "analysis" / "study-provenance"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "README.md").write_text(
            "# 分析计划\n\n当前确认性分析使用固定规则评估主要差异。\n",
            encoding="utf-8",
        )
        (analysis_dir / "run.py").write_text("print('ok')\n", encoding="utf-8")

        with self.assertRaisesRegex(ResearchDbError, "study/EXECUTION_REPORT.md"):
            record_analysis(
                self.root,
                {
                    "slug": "study-provenance",
                    "title": "实施来源语言检查",
                    "analysis_mode": "confirmatory",
                    "status": "frozen",
                    "target_uncertainty": "主要差异是否存在",
                    "estimand": "主要差异",
                    "unit_of_inference": "sample",
                    "primary_analysis": "固定规则",
                    "analysis_path": "analysis/study-provenance/README.md",
                    "code_path": "analysis/study-provenance/run.py",
                    "freeze_commit": "freeze-placeholder",
                    "dataset_slugs": ["dataset-language"],
                },
            )

    def test_analysis_freeze_runs_language_preflight_before_persisting(self) -> None:
        self._record_language_dataset()
        analysis_dir = self.root / "analysis" / "language-freeze"
        analysis_dir.mkdir(parents=True)
        plan = analysis_dir / "README.md"
        plan.write_text(
            "# 分析计划\n\n当前 exploratory analysis 使用 randomization 检验主要差异。\n",
            encoding="utf-8",
        )
        code = analysis_dir / "run.py"
        code.write_text("print('ok')\n", encoding="utf-8")
        bundle = {
            "slug": "language-freeze",
            "title": "冻结前语言测试",
            "analysis_mode": "confirmatory",
            "status": "frozen",
            "target_uncertainty": "主要差异是否存在",
            "estimand": "主要差异",
            "unit_of_inference": "sample",
            "primary_analysis": "固定的重抽样检验",
            "analysis_path": "analysis/language-freeze/README.md",
            "code_path": "analysis/language-freeze/run.py",
            "freeze_commit": "freeze-placeholder",
            "dataset_slugs": ["dataset-language"],
        }

        with self.assertRaisesRegex(ResearchDbError, "冻结前学术语言检查失败"):
            record_analysis(self.root, bundle)

        with closing(sqlite3.connect(database_path(self.root))) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM analysis_runs WHERE slug = 'language-freeze'"
                ).fetchone()[0],
                0,
            )

        plan.write_text(
            "# 分析计划\n\n当前确认性分析使用固定的随机化检验评估主要差异。\n",
            encoding="utf-8",
        )
        result = record_analysis(self.root, bundle)
        self.assertEqual(result["status"], "frozen")


if __name__ == "__main__":
    unittest.main()
