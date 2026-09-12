from __future__ import annotations

from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import ResearchDbError, apply_migrations, database_path, init_database, validate  # noqa: E402
from research_db_ops.planning import (  # noqa: E402
    list_hypothesis_proposals,
    list_research_judgments,
    list_user_hypothesis_decisions,
    record_hypothesis_proposal,
    record_hypothesis_set,
    record_research_judgment,
    record_user_hypothesis_decision,
)
from research_db_support.schema import list_migrations  # noqa: E402


class HypothesisProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        (self.root / "hypotheses").mkdir()
        (self.root / "hypotheses" / "source.md").write_text(
            "# 假设集合\n\n保留多个竞争解释。\n", encoding="utf-8"
        )
        init_database(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_user_origin_survives_later_agent_operationalization_and_user_acceptance(self) -> None:
        source_bundle = {
            "slug": "oxygen-dependent-source",
            "origin": "user",
            "original_statement": "会不会只有低氧时 X 才真正贡献目标代谢物？",
            "source_context": "用户主动提出的科学猜想。",
        }
        record_hypothesis_proposal(self.root, source_bundle)
        record_hypothesis_proposal(
            self.root,
            {
                **source_bundle,
                "operationalized_statement": "候选菌 X 对目标代谢物的来源贡献随氧条件改变。",
                "operationalized_by": "agent",
            },
        )
        record_user_hypothesis_decision(
            self.root,
            {
                "proposal_slug": "oxygen-dependent-source",
                "decision": "accepted_for_exploration",
                "source_statement": "这个方向值得继续查。",
            },
        )

        proposals = list_hypothesis_proposals(self.root)["hypothesis_proposals"]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["origin"], "user")
        self.assertEqual(proposals[0]["operationalized_by"], "agent")
        self.assertEqual(
            proposals[0]["latest_user_decision"]["decision"],
            "accepted_for_exploration",
        )

        decisions = list_user_hypothesis_decisions(
            self.root, proposal_slug="oxygen-dependent-source"
        )["user_hypothesis_decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["source_statement"], "这个方向值得继续查。")

    def test_agent_and_user_judgments_are_distinct_attributed_records(self) -> None:
        record_hypothesis_proposal(
            self.root,
            {
                "slug": "community-marker",
                "origin": "agent",
                "original_statement": "X 可能只是共同群落状态的标志物。",
                "rationale": "X 与多个分类单元共同变化，且缺少来源特异功能测量。",
            },
        )
        record_research_judgment(
            self.root,
            {
                "actor": "agent",
                "judgment_type": "recommendation",
                "statement": "优先寻找来源分辨率证据。",
                "basis": "当前证据不能区分 X 的来源贡献与共同变化。",
                "proposal_slug": "community-marker",
            },
        )
        record_research_judgment(
            self.root,
            {
                "actor": "user",
                "judgment_type": "research_priority",
                "statement": "优先推进机制方向。",
                "source_statement": "我希望这个项目优先做机制，不优先做预测。",
                "proposal_slug": "community-marker",
            },
        )

        agent_rows = list_research_judgments(self.root, actor="agent")["research_judgments"]
        user_rows = list_research_judgments(self.root, actor="user")["research_judgments"]
        self.assertEqual(len(agent_rows), 1)
        self.assertEqual(len(user_rows), 1)
        self.assertEqual(agent_rows[0]["actor"], "agent")
        self.assertEqual(user_rows[0]["actor"], "user")
        self.assertIn("项目优先做机制", user_rows[0]["source_statement"])

    def test_hypothesis_proposal_source_fields_are_immutable(self) -> None:
        bundle = {
            "slug": "direct-effect",
            "origin": "agent",
            "original_statement": "目标因素可能具有直接作用。",
            "rationale": "当前证据仍允许直接作用解释。",
        }
        record_hypothesis_proposal(self.root, bundle)
        changed = dict(bundle)
        changed["original_statement"] = "目标因素一定具有直接作用。"
        with self.assertRaisesRegex(ResearchDbError, "不可覆盖"):
            record_hypothesis_proposal(self.root, changed)

    def test_modified_user_decision_requires_new_resulting_proposal(self) -> None:
        record_hypothesis_proposal(
            self.root,
            {
                "slug": "direct-source",
                "origin": "agent",
                "original_statement": "X 可能直接贡献目标代谢物。",
                "rationale": "当前证据仍允许直接来源解释。",
            },
        )
        with self.assertRaisesRegex(ResearchDbError, "resulting_proposal_slug"):
            record_user_hypothesis_decision(
                self.root,
                {
                    "proposal_slug": "direct-source",
                    "decision": "modified",
                    "source_statement": "我想把它改成只在低氧条件下成立。",
                },
            )

        record_hypothesis_proposal(
            self.root,
            {
                "slug": "low-oxygen-direct-source",
                "origin": "user",
                "original_statement": "X 的直接来源贡献可能只在低氧条件下成立。",
                "source_context": "用户对已有 Agent proposal 的明确修改。",
            },
        )
        result = record_user_hypothesis_decision(
            self.root,
            {
                "proposal_slug": "direct-source",
                "decision": "modified",
                "source_statement": "我想把它改成只在低氧条件下成立。",
                "resulting_proposal_slug": "low-oxygen-direct-source",
            },
        )
        self.assertEqual(result["resulting_proposal_slug"], "low-oxygen-direct-source")

    def test_new_hypothesis_set_requires_proposal_link(self) -> None:
        with self.assertRaisesRegex(ResearchDbError, "proposal_slugs"):
            record_hypothesis_set(
                self.root,
                {
                    "slug": "source",
                    "title": "来源归因假设集合",
                    "target_uncertainty": "X 是否具有来源特异贡献？",
                    "artifact_path": "hypotheses/source.md",
                    "status": "draft",
                },
            )

        record_hypothesis_proposal(
            self.root,
            {
                "slug": "source-specific-contribution",
                "origin": "agent",
                "original_statement": "X 可能具有来源特异贡献。",
                "rationale": "该解释需要与共同变化模型竞争。",
            },
        )
        result = record_hypothesis_set(
            self.root,
            {
                "slug": "source",
                "title": "来源归因假设集合",
                "target_uncertainty": "X 是否具有来源特异贡献？",
                "artifact_path": "hypotheses/source.md",
                "status": "draft",
                "proposal_slugs": ["source-specific-contribution"],
            },
        )
        self.assertEqual(result["proposal_slugs"], ["source-specific-contribution"])

    def test_v17_hypothesis_set_is_grandfathered_after_migration(self) -> None:
        legacy_root = self.root / "legacy"
        legacy_root.mkdir()
        (legacy_root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        (legacy_root / "hypotheses").mkdir()
        (legacy_root / "hypotheses" / "legacy.md").write_text("# 旧假设集合\n", encoding="utf-8")
        db_path = database_path(legacy_root)
        db_path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(db_path)) as connection, connection:
            for migration in list_migrations():
                if migration.version > 17:
                    break
                connection.executescript(migration.path.read_text(encoding="utf-8"))
                connection.execute(f"PRAGMA user_version = {migration.version}")
                connection.execute(
                    """
                    INSERT INTO meta(key, value) VALUES('schema_version', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (str(migration.version),),
                )
            connection.execute(
                """
                INSERT INTO hypothesis_sets(
                    slug, title, target_uncertainty, artifact_path, status,
                    freeze_commit, created_at, updated_at
                ) VALUES (
                    'legacy', '旧假设集合', '旧问题', 'hypotheses/legacy.md', 'draft',
                    NULL, '2026-08-01T00:00:00+00:00', '2026-08-01T00:00:00+00:00'
                )
                """
            )

        self.assertEqual(apply_migrations(db_path), [18, 19, 20, 21, 22, 23])
        result = validate(legacy_root)
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
