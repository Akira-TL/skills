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

    def test_analysis_freeze_runs_language_preflight_before_persisting(self) -> None:
        data_dir = self.root / "data"
        data_dir.mkdir()
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
