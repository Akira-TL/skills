from __future__ import annotations

from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import MIGRATION_DIR, database_path, init_database  # noqa: E402
from research_db_ops.planning import (  # noqa: E402
    record_design,
    record_hypothesis_proposal,
    record_hypothesis_set,
)
from research_db_ops.completion import (  # noqa: E402
    academic_language_readiness,
    literature_completion_readiness,
    planning_completion_readiness,
    project_state_readiness,
    validate_completion,
)


VALID_RESEARCH_MD = """# Research

## Objective

验证科研完成门禁。

## Current Loop

QUESTION

## Active Uncertainty

当前最需要区分的科学解释是什么？

## Current State

当前证据状态已记录。

## Active Work

等待下一条能够区分竞争解释的证据。

## Open Threads

暂无当前优先处理的其他问题。

## Key Decisions

保持当前证据边界。

## References

- `.research/research.sqlite`
"""


class ResearchCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text(VALID_RESEARCH_MD, encoding="utf-8")
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

    def test_completion_rejects_repository_without_commit(self) -> None:
        result = validate_completion(self.root)

        self.assertFalse(result["ok"])
        self.assertTrue(any("尚无任何 Git commit" in error for error in result["errors"]))
        self.assertTrue(any("尚未被 Git 跟踪" in error for error in result["errors"]))

    def test_completion_returns_migration_gate_for_legacy_schema(self) -> None:
        db_path = database_path(self.root)
        db_path.unlink()
        with closing(sqlite3.connect(db_path)) as connection, connection:
            for migration in sorted(MIGRATION_DIR.rglob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration.name[:3])
                if version > 11:
                    break
                connection.executescript(migration.read_text(encoding="utf-8"))
            connection.execute("PRAGMA user_version = 11")
            connection.execute("DELETE FROM meta WHERE key = 'schema_version'")
            connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', '11')"
            )

        result = validate_completion(self.root)

        self.assertFalse(result["ok"])
        self.assertFalse(result["completion"])
        self.assertTrue(result["completion_checked"])
        self.assertFalse(result["schema_compatible"])
        self.assertTrue(any("schema version 为 v11" in error for error in result["errors"]))
        self.assertFalse(result["discovery"]["checked"])
        self.assertEqual(result["discovery"]["blockers"][0]["reason"], "schema_incompatible")

    def test_completion_git_result_keeps_dirty_canonical_paths_key(self) -> None:
        result = validate_completion(self.root)

        self.assertIn("dirty_canonical_paths", result["git"])
        self.assertNotIn("dirtycanonical_paths", result["git"])

    def test_project_state_requires_required_sections(self) -> None:
        (self.root / "RESEARCH.md").write_text(
            "# Research\n\n## Objective\n\n测试。\n\n## Current Loop\n\nQUESTION\n",
            encoding="utf-8",
        )

        result = project_state_readiness(self.root)

        self.assertFalse(result["ready"])
        blocker = next(
            item for item in result["blockers"]
            if item["reason"] == "research_state_missing_sections"
        )
        self.assertIn("Active Work", blocker["sections"])
        self.assertIn("Open Threads", blocker["sections"])

    def test_project_state_rejects_stale_completion_active_work(self) -> None:
        stale = VALID_RESEARCH_MD.replace(
            "等待下一条能够区分竞争解释的证据。",
            "当前正在完成最终 Git commit，并运行 research-db validate --completion。",
        )
        (self.root / "RESEARCH.md").write_text(stale, encoding="utf-8")

        result = project_state_readiness(self.root)

        self.assertFalse(result["ready"])
        self.assertTrue(
            any(
                item["reason"] == "research_state_active_work_stale_completion"
                for item in result["blockers"]
            )
        )

    def test_project_state_rejects_stale_bootstrap_active_work(self) -> None:
        stale = VALID_RESEARCH_MD.replace(
            "等待下一条能够区分竞争解释的证据。",
            "正在执行项目 bootstrap：初始化 Git 仓库、科研知识数据库与 RESEARCH.md。",
        )
        (self.root / "RESEARCH.md").write_text(stale, encoding="utf-8")

        result = project_state_readiness(self.root)

        self.assertFalse(result["ready"])
        blocker = next(
            item
            for item in result["blockers"]
            if item["reason"] == "research_state_active_work_stale_completion"
        )
        self.assertIn("bootstrap", blocker["markers"])

    def test_project_state_rejects_evidence_status_as_competing_explanation(self) -> None:
        invalid = VALID_RESEARCH_MD.replace(
            "当前最需要区分的科学解释是什么？",
            """Question: 候选中介是否承担非零因果中介作用？

Competing explanations:
- E1：候选中介承担非零因果中介作用。
- E2：现有相关与回归系数衰减不足以区分候选中介的因果作用，因此当前证据不能识别中介效应。

Discriminating gap: 缺少能够区分候选中介作用与其他处理后路径的判别证据。

Best next evidence: 定义可识别的中介估计目标并取得对应判别证据。""",
        )
        (self.root / "RESEARCH.md").write_text(invalid, encoding="utf-8")

        result = project_state_readiness(self.root)

        self.assertFalse(result["ready"])
        blocker = next(
            item
            for item in result["blockers"]
            if item["reason"] == "research_state_competing_explanation_is_evidence_status"
        )
        self.assertIn("不足以区分", blocker["markers"])
        self.assertIn("当前证据不能", blocker["markers"])

    def test_project_state_accepts_scientific_competing_explanation(self) -> None:
        valid = VALID_RESEARCH_MD.replace(
            "当前最需要区分的科学解释是什么？",
            """Question: 候选中介是否承担非零因果中介作用？

Competing explanations:
- E1：候选中介承担非零因果中介作用。
- E2：总处理效应主要经候选中介以外的处理诱导路径产生，候选中介不是该总效应的必要因果中介。

Discriminating gap: 当前普通条件回归不能区分这两个科学状态。

Best next evidence: 定义可识别的中介估计目标并取得对应判别证据。""",
        )
        (self.root / "RESEARCH.md").write_text(valid, encoding="utf-8")

        result = project_state_readiness(self.root)

        self.assertTrue(result["ready"], result["blockers"])

    def _insert_reviewed_candidate(
        self,
        candidate_id: int,
        paper_id: str,
        *,
        priority: str = "normal",
        depth: str = "full_scan",
    ) -> None:
        now = "2026-08-27T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, status, read_depth, reading_status, critical_status,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', ?, 'extracted', 'critically_reviewed', ?, ?)
                """,
                (paper_id, f"Paper {paper_id}", depth, now, now),
            )
            connection.execute(
                """
                INSERT INTO candidates(
                    id, title, identity_status, relevance_status, paper_id,
                    created_at, updated_at, acquisition_status, reading_priority
                ) VALUES (?, ?, 'resolved', 'relevant', ?, ?, ?, 'acquired', ?)
                """,
                (candidate_id, f"Candidate {candidate_id}", paper_id, now, now, priority),
            )
            connection.execute(
                """
                INSERT INTO acquisition_attempts(
                    candidate_id, target_kind, route_family, resource_kind, source_url,
                    outcome, detail, attempted_at, access_basis, access_basis_detail
                ) VALUES (?, 'main_text', 'publisher', 'full_text_html', ?,
                          'acquired', 'Verified publisher full text.', ?,
                          'publisher_open', 'Publisher-hosted open full text verified for test.')
                """,
                (candidate_id, f"https://publisher.example/{candidate_id}", now),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked, extraction_checks_json
                ) VALUES (?, 'reconstruction', ?, ?, ?, '[]', '[\"Methods > design\"]',
                          '{\"observation_semantics_checked\": true}')
                """,
                (paper_id, depth, now, now),
            )
            connection.execute(
                """
                INSERT INTO reading_runs(
                    paper_id, pass, depth, started_at, completed_at,
                    artifacts_checked, sections_checked
                ) VALUES (?, 'critical_audit', ?, ?, ?, '[]', '[\"Discussion > limitations\"]')
                """,
                (paper_id, depth, now, now),
            )

    def test_literature_completion_rejects_unverified_acquired_source(self) -> None:
        self._insert_reviewed_candidate(1, "P000001")
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                "UPDATE acquisition_attempts SET access_basis='unverified', "
                "access_basis_detail='Legacy mirror with no verified authorization basis' "
                "WHERE candidate_id=1"
            )
        result = literature_completion_readiness(self.root, {"relevant_candidate_count": 1})
        reasons = {item["reason"] for item in result["blockers"]}
        self.assertIn("acquired_main_text_access_basis_unverified", reasons)

    def test_targeted_direct_ingest_paper_requires_full_review(self) -> None:
        now = "2026-08-27T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                """
                INSERT INTO papers(
                    id, title, status, read_depth, reading_status, critical_status,
                    created_at, updated_at
                ) VALUES ('P000001', 'Targeted paper', 'active', 'full_scan',
                          'unread', 'not_reviewed', ?, ?)
                """,
                (now, now),
            )
            connection.execute(
                """
                INSERT INTO acquisition_attempts(
                    paper_id, target_kind, route_family, resource_kind, source_url,
                    outcome, detail, attempted_at, access_basis, access_basis_detail
                ) VALUES ('P000001', 'main_text', 'repository', 'xml',
                          'https://pmc.ncbi.nlm.nih.gov/articles/test/', 'acquired',
                          'Targeted full text acquired.', ?, 'public_repository',
                          'Public repository full text verified for test.')
                """,
                (now,),
            )
        first = literature_completion_readiness(self.root, {"relevant_candidate_count": 0})
        reasons = {item["reason"] for item in first["blockers"]}
        self.assertIn("targeted_paper_not_fully_reviewed", reasons)

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                "UPDATE papers SET reading_status='extracted', critical_status='critically_reviewed' "
                "WHERE id='P000001'"
            )
        second = literature_completion_readiness(self.root, {"relevant_candidate_count": 0})
        self.assertTrue(second["ready"], second["blockers"])

    def test_literature_completion_requires_core_deep_extraction(self) -> None:
        self._insert_reviewed_candidate(1, "P000001", priority="core", depth="full_scan")

        first = literature_completion_readiness(self.root, {"relevant_candidate_count": 1})
        reasons = {item["reason"] for item in first["blockers"]}
        self.assertIn("core_acquired_not_deep_extraction", reasons)

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                "UPDATE papers SET read_depth = 'deep_extraction' WHERE id = 'P000001'"
            )
            connection.execute(
                "UPDATE reading_runs SET depth = 'deep_extraction' WHERE paper_id = 'P000001'"
            )
        second = literature_completion_readiness(self.root, {"relevant_candidate_count": 1})
        self.assertTrue(second["ready"])

    def test_literature_completion_requires_cross_paper_scientific_relation(self) -> None:
        self._insert_reviewed_candidate(1, "P000001")
        self._insert_reviewed_candidate(2, "P000002")
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                "INSERT INTO claims(paper_id, statement, claim_type) VALUES ('P000001', 'Claim A', 'descriptive')"
            )
            connection.execute(
                "INSERT INTO claims(paper_id, statement, claim_type) VALUES ('P000002', 'Claim B', 'descriptive')"
            )
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id, note, created_at
                ) VALUES ('paper', 'P000001', 'SHARES_DATA_WITH', 'paper', 'P000002',
                          'Shared dataset.', '2026-08-27T00:00:00+00:00')
                """
            )

        discovery = {
            "relevant_candidate_count": 2,
            "discovery_families": ["query_search", "citation_chasing"],
        }
        first = literature_completion_readiness(self.root, discovery)
        self.assertFalse(first["ready"])
        self.assertTrue(
            any(
                item["reason"] == "cross_paper_scientific_relation_missing"
                for item in first["blockers"]
            )
        )

        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            claim_ids = [row[0] for row in connection.execute("SELECT id FROM claims ORDER BY id")]
            connection.execute(
                """
                INSERT INTO relations(
                    subject_type, subject_id, predicate, object_type, object_id, note, created_at
                ) VALUES ('claim', ?, 'QUALIFIES', 'claim', ?,
                          'Paper 2 narrows the scope of Paper 1.', '2026-08-27T00:00:00+00:00')
                """,
                (str(claim_ids[1]), str(claim_ids[0])),
            )
        second = literature_completion_readiness(self.root, discovery)
        self.assertTrue(second["ready"])
        self.assertEqual(second["cross_paper_scientific_relation_count"], 1)

    def test_chinese_project_rejects_long_english_scientific_prose(self) -> None:
        (self.root / "RESEARCH.md").write_text(
            "# 研究\n\n这是一个中文科研项目，用于验证规范中文学术写作要求。"
            "研究问题、证据边界、方法判断和最终结论均应采用中文表述。"
            "这里继续补足足够的中文字符，使系统能够明确判断当前项目的人类可读科研语言是中文。\n",
            encoding="utf-8",
        )
        sidecar = self.root / "paper-note.md"
        sidecar.write_text(
            "# 论文笔记\n\n"
            "This paragraph is intentionally written as long English scientific prose to verify that a Chinese research project cannot silently finish with an English narrative sidecar. It contains enough ordinary English words to represent a real paragraph rather than a paper title, identifier, abbreviation, or required terminology annotation.\n",
            encoding="utf-8",
        )
        now = "2026-08-27T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                """
                INSERT INTO papers(id, title, status, sidecar_path, created_at, updated_at)
                VALUES ('P000001', 'Language test paper', 'active', 'paper-note.md', ?, ?)
                """,
                (now, now),
            )
        result = academic_language_readiness(self.root)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"][0]["reason"], "english_prose_in_chinese_research_text")

    def test_chinese_research_state_rejects_bare_mature_english_terms(self) -> None:
        (self.root / "RESEARCH.md").write_text(
            "# 研究\n\n这是一个中文科研项目，用于验证规范中文学术术语要求。"
            "当前科研状态、证据边界和后续工作均应采用已有的中文学术表述，"
            "不能因为内部工作流方便就把成熟术语长期保留为裸英文。\n\n"
            "## Current State\n\n当前 exploratory analysis 只用于生成后续研究线索。\n",
            encoding="utf-8",
        )

        result = academic_language_readiness(self.root)

        self.assertFalse(result["ready"])
        blockers = [
            item
            for item in result["blockers"]
            if item["reason"] == "bare_english_term_in_chinese_research_text"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["path"], "RESEARCH.md")
        self.assertEqual(blockers[0]["terms"], ["analysis", "exploratory"])

    def test_academic_language_grandfathers_unchanged_legacy_text_after_migration(self) -> None:
        legacy_text = (
            "# Research\n\n"
            "这是一个迁移前已经形成版本历史的中文科研项目。当前问题、证据边界、"
            "结果解释与后续研究方向都已经保存，而且这些历史内容不能仅因后来新增的"
            "写作规范而被迫改写，否则会破坏结果可见前的版本审计与科研溯源。\n\n"
            "## Current State\n\n"
            "历史记录使用 Treatment A 表示当时已经冻结的处理标签。\n"
        )
        (self.root / "RESEARCH.md").write_text(legacy_text, encoding="utf-8")

        db_path = database_path(self.root)
        db_path.unlink()
        with closing(sqlite3.connect(db_path)) as connection, connection:
            for migration in sorted(MIGRATION_DIR.rglob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration.name[:3])
                if version > 14:
                    break
                connection.executescript(migration.read_text(encoding="utf-8"))
            connection.execute("PRAGMA user_version = 14")
            connection.execute("DELETE FROM meta WHERE key = 'schema_version'")
            connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', '14')"
            )

        subprocess.run(
            ["git", "-C", str(self.root), "add", "RESEARCH.md", ".research/research.sqlite"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "RESEARCH: legacy baseline"],
            check=True,
            capture_output=True,
        )
        baseline = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        migrated = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "research_db.py"),
                "--project",
                str(self.root),
                "migrate",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)

        unchanged = academic_language_readiness(self.root)
        self.assertTrue(unchanged["ready"], unchanged["blockers"])
        with closing(sqlite3.connect(db_path)) as connection:
            marker = connection.execute(
                "SELECT value FROM meta WHERE key = 'academic_language_legacy_baseline_commit'"
            ).fetchone()
        self.assertIsNotNone(marker)
        self.assertEqual(marker[0], baseline)

        (self.root / "RESEARCH.md").write_text(
            legacy_text + "\n迁移后新增的 exploratory analysis 只用于测试新文本仍受规范约束。\n",
            encoding="utf-8",
        )
        changed = academic_language_readiness(self.root)
        blockers = [
            item
            for item in changed["blockers"]
            if item["reason"] == "bare_english_term_in_chinese_research_text"
        ]
        self.assertFalse(changed["ready"])
        self.assertTrue(any(item["path"] == "RESEARCH.md" for item in blockers))

    def test_academic_language_checks_registered_analysis_markdown_artifacts(self) -> None:
        (self.root / "RESEARCH.md").write_text(
            "# 研究\n\n这是一个中文科研项目，用于验证登记到分析对象的人类可读结果解释也受学术语言规范约束。"
            "当前研究问题、证据边界、统计结果与后续判断均采用规范中文科研表述。\n",
            encoding="utf-8",
        )
        analysis_dir = self.root / "analysis" / "example"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "README.md").write_text(
            "# 分析入口\n\n主要结果与解释均在登记的分析文件中保存。\n",
            encoding="utf-8",
        )
        interpretation = analysis_dir / "INTERPRETATION.md"
        interpretation.write_text(
            "# 结果解释\n\n当前 exploratory analysis 仅用于生成后续研究线索。\n",
            encoding="utf-8",
        )
        now = "2026-08-30T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO analysis_runs(
                    slug, title, analysis_mode, status, target_uncertainty, estimand,
                    unit_of_inference, primary_analysis, analysis_path, code_path,
                    started_at, created_at, updated_at
                ) VALUES (
                    'example', '示例分析', 'exploratory', 'planned', '测试问题', '测试估计量',
                    'participant', '测试分析', 'analysis/example/README.md',
                    'analysis/example/README.md', ?, ?, ?
                )
                """,
                (now, now, now),
            )
            connection.execute(
                """
                INSERT INTO analysis_artifacts(
                    analysis_id, role, path, git_tracking, created_at
                ) VALUES (?, 'other', 'analysis/example/INTERPRETATION.md', 'required', ?)
                """,
                (int(cursor.lastrowid), now),
            )

        result = academic_language_readiness(self.root)

        self.assertFalse(result["ready"])
        blockers = [
            item
            for item in result["blockers"]
            if item["reason"] == "bare_english_term_in_chinese_research_text"
        ]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["path"], "analysis/example/INTERPRETATION.md")
        self.assertEqual(blockers[0]["terms"], ["analysis", "exploratory"])

    def test_academic_language_ignores_inline_code_paths(self) -> None:
        (self.root / "RESEARCH.md").write_text(
            "# 研究\n\n这是一个中文科研项目，用于验证分析文件路径不会被误判为英文科研叙述。"
            "这里补足中文上下文，确保语言检查处于启用状态，并保留规范中文学术表述。\n",
            encoding="utf-8",
        )
        analysis_dir = self.root / "analysis" / "example"
        analysis_dir.mkdir(parents=True)
        analysis_note = analysis_dir / "README.md"
        analysis_note.write_text(
            "# 分析输出\n\n"
            "以下为结果文件：\n"
            "- `outputs/estimates/primary_estimates.csv`\n"
            "- `outputs/estimates/random_effect_summary.csv`\n"
            "- `outputs/diagnostics/primary_model.txt`\n"
            "- `outputs/figures/residual_vs_fitted.png`\n"
            "- `outputs/figures/residual_qq.png`\n",
            encoding="utf-8",
        )
        now = "2026-08-27T00:00:00+00:00"
        with closing(sqlite3.connect(database_path(self.root))) as connection, connection:
            connection.execute(
                """
                INSERT INTO analysis_runs(
                    slug, title, analysis_mode, status, target_uncertainty, estimand,
                    unit_of_inference, primary_analysis, analysis_path, code_path,
                    started_at, created_at, updated_at
                ) VALUES (
                    'example', '示例分析', 'exploratory', 'planned', '测试问题', '测试估计量',
                    'participant', '测试分析', 'analysis/example/README.md',
                    'analysis/example/README.md', ?, ?, ?
                )
                """,
                (now, now, now),
            )
        result = academic_language_readiness(self.root)
        self.assertTrue(result["ready"], result["blockers"])

    def test_planning_completion_requires_registered_frozen_artifacts(self) -> None:
        hypotheses = self.root / "hypotheses"
        designs = self.root / "designs"
        hypotheses.mkdir()
        designs.mkdir()
        hypothesis_path = hypotheses / "causal-set.md"
        design_path = designs / "causal-design.md"
        hypothesis_path.write_text("# 假设集合\n\nH1 与 H2 给出不同预测。\n", encoding="utf-8")
        design_path.write_text("# 研究设计\n\n主要估计目标与实验单位已经定义。\n", encoding="utf-8")

        orphaned = planning_completion_readiness(self.root)
        reasons = {item["reason"] for item in orphaned["blockers"]}
        self.assertIn("hypothesis_artifacts_unregistered", reasons)
        self.assertIn("design_artifacts_unregistered", reasons)

        subprocess.run(
            ["git", "-C", str(self.root), "add", "RESEARCH.md", ".research/research.sqlite", "hypotheses", "designs"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "RESEARCH: freeze hypothesis and design"],
            check=True,
            capture_output=True,
        )
        freeze_commit = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        record_hypothesis_proposal(
            self.root,
            {
                "slug": "causal-direct-effect",
                "origin": "agent",
                "original_statement": "目标因素可能具有独立因果贡献。",
                "rationale": "该解释与当前目标不确定性一致，并需要与替代解释形成可判别预测。",
            },
        )
        record_hypothesis_set(
            self.root,
            {
                "slug": "causal-set",
                "title": "因果竞争假设",
                "target_uncertainty": "目标因素是否具有独立因果贡献？",
                "artifact_path": "hypotheses/causal-set.md",
                "status": "frozen",
                "freeze_commit": freeze_commit,
                "proposal_slugs": ["causal-direct-effect"],
            },
        )
        record_design(
            self.root,
            {
                "slug": "causal-design",
                "title": "因果判别设计",
                "hypothesis_set_slug": "causal-set",
                "target_estimand": "干预组与对照组的主要结局差异",
                "primary_outcome": "主要结局",
                "experimental_unit": "独立随机化集群",
                "artifact_path": "designs/causal-design.md",
                "status": "frozen",
                "feasibility_status": "unresolved",
                "feasibility_summary": "关键设施和精度参数仍需确认。",
                "freeze_commit": freeze_commit,
            },
        )
        ready = planning_completion_readiness(self.root)
        self.assertTrue(ready["ready"], ready["blockers"])
        self.assertEqual(ready["hypothesis_set_count"], 1)
        self.assertEqual(ready["design_count"], 1)
        self.assertEqual(ready["frozen_design_count"], 1)

        subprocess.run(
            ["git", "-C", str(self.root), "add", ".research/research.sqlite"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "CHORE: register planning provenance"],
            check=True,
            capture_output=True,
        )
        clean = validate_completion(self.root)
        self.assertTrue(clean["ok"], clean["errors"])
        self.assertIn("hypotheses/causal-set.md", clean["git"]["canonical_paths"])
        self.assertIn("designs/causal-design.md", clean["git"]["canonical_paths"])

        design_path.write_text("# 研究设计\n\n冻结后的设计被未经提交地修改。\n", encoding="utf-8")
        dirty = validate_completion(self.root)
        self.assertFalse(dirty["ok"])
        self.assertTrue(any("designs/causal-design.md" in error for error in dirty["errors"]))

    def test_completion_requires_committed_canonical_research_state(self) -> None:
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "add",
                "RESEARCH.md",
                ".research/research.sqlite",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "RESEARCH: bootstrap project"],
            check=True,
            capture_output=True,
        )

        clean = validate_completion(self.root)
        self.assertTrue(clean["ok"])
        self.assertIsNotNone(clean["git"]["head"])

        (self.root / "RESEARCH.md").write_text("# Research\n\nchanged\n", encoding="utf-8")
        dirty = validate_completion(self.root)
        self.assertFalse(dirty["ok"])
        self.assertTrue(any("未提交修改" in error for error in dirty["errors"]))


if __name__ == "__main__":
    unittest.main()
