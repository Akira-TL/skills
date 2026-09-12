from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import init_database  # noqa: E402
from research_db_ops.downstream import record_analysis_attempt  # noqa: E402
from research_db_ops.completion.project import research_tree_completion_readiness  # noqa: E402
from research_db_ops.project import (  # noqa: E402
    record_research_branch,
    record_research_node,
    set_research_tree_state,
)
from research_db_ops.user_reading import (  # noqa: E402
    confirmation_control,
    sync_user_reading,
    user_reading_status,
)
from research_db_support.storage import ResearchDbError, connect, database_path  # noqa: E402


class ResearchGitAttemptReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-b", "main", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "research@example.test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Research Test"], check=True)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)
        self._commit("bootstrap")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _commit(self, message: str) -> str:
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-m", message], check=True, capture_output=True)
        return subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()

    def test_init_writes_targeted_gitignore_defaults(self) -> None:
        text = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".research/artifacts/", text)
        self.assertIn("literature/papers/*.pdf", text)
        self.assertIn("analysis/**/figures/*.png", text)
        self.assertNotIn("*.pdf", text.splitlines())

    def test_research_branch_name_and_merge_provenance(self) -> None:
        record_research_node(
            self.root,
            {
                "slug": "question-main",
                "kind": "question",
                "label": "Primary question",
                "workflow_status": "active",
                "branch_priority": "primary",
            },
        )
        branch = "research/question/question-main"
        subprocess.run(["git", "-C", str(self.root), "switch", "-c", branch], check=True, capture_output=True)
        (self.root / "branch-note.md").write_text("branch\n", encoding="utf-8")
        self._commit("branch work")

        active = record_research_branch(
            self.root,
            {"node_slug": "question-main", "disposition": "active"},
        )
        self.assertEqual(active["branch_name"], branch)
        self.assertEqual(active["disposition"], "active")
        self._commit("record branch provenance")

        subprocess.run(["git", "-C", str(self.root), "switch", "main"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "merge", "--no-ff", branch, "-m", "accept question branch"],
            check=True,
            capture_output=True,
        )
        merged = record_research_branch(
            self.root,
            {
                "node_slug": "question-main",
                "disposition": "merged",
                "closure_reason": "Accepted into canonical research state.",
            },
        )
        self.assertEqual(merged["disposition"], "merged")
        self.assertTrue(merged["final_ref"])

    def test_merge_rejects_branch_when_main_advanced_after_fork(self) -> None:
        record_research_node(
            self.root,
            {
                "slug": "stale-route",
                "kind": "analysis",
                "label": "Stale route",
                "workflow_status": "active",
            },
        )
        branch = "research/analysis/stale-route"
        subprocess.run(["git", "-C", str(self.root), "switch", "-c", branch], check=True, capture_output=True)
        (self.root / "route.py").write_text("print('route')\n", encoding="utf-8")
        self._commit("route work")
        record_research_branch(
            self.root,
            {"node_slug": "stale-route", "disposition": "active"},
        )
        self._commit("record route provenance")

        subprocess.run(["git", "-C", str(self.root), "switch", "main"], check=True, capture_output=True)
        (self.root / "main-note.md").write_text("main advanced\n", encoding="utf-8")
        self._commit("advance canonical main")
        subprocess.run(
            ["git", "-C", str(self.root), "merge", "--no-ff", branch, "-m", "merge stale route"],
            check=True,
            capture_output=True,
        )
        with self.assertRaisesRegex(ResearchDbError, "main 已经推进"):
            record_research_branch(
                self.root,
                {
                    "node_slug": "stale-route",
                    "disposition": "merged",
                    "closure_reason": "Attempted stale merge.",
                },
            )

    def test_active_branch_allows_only_provenance_commit_after_recorded_tip(self) -> None:
        record_research_node(
            self.root,
            {
                "slug": "objective-root",
                "kind": "objective",
                "label": "Objective",
                "workflow_status": "active",
                "branch_priority": "primary",
            },
        )
        record_research_node(
            self.root,
            {
                "slug": "analysis-route",
                "kind": "analysis",
                "label": "Analysis route",
                "parent_slug": "objective-root",
                "workflow_status": "active",
            },
        )
        set_research_tree_state(
            self.root,
            {"root_slug": "objective-root", "active_slug": "analysis-route"},
        )
        branch = "research/analysis/analysis-route"
        subprocess.run(["git", "-C", str(self.root), "switch", "-c", branch], check=True, capture_output=True)
        (self.root / "scripts" / "analyses").mkdir(parents=True)
        (self.root / "scripts" / "analyses" / "route.py").write_text("print('route')\n", encoding="utf-8")
        scientific_tip = self._commit("scientific route")
        recorded = record_research_branch(
            self.root,
            {"node_slug": "analysis-route", "disposition": "active"},
        )
        self.assertEqual(recorded["tip_commit"], scientific_tip)
        self._commit("record branch provenance")

        readiness = research_tree_completion_readiness(self.root)
        reasons = {item["reason"] for item in readiness["blockers"]}
        self.assertNotIn("research_git_active_branch_out_of_sync", reasons)

        (self.root / "scripts" / "analyses" / "route.py").write_text("print('changed')\n", encoding="utf-8")
        self._commit("change scientific route")
        stale = research_tree_completion_readiness(self.root)
        stale_reasons = {item["reason"] for item in stale["blockers"]}
        self.assertIn("research_git_active_branch_out_of_sync", stale_reasons)

    def test_archived_branch_uses_annotated_tag_after_closure_provenance(self) -> None:
        record_research_node(
            self.root,
            {
                "slug": "objective-root",
                "kind": "objective",
                "label": "Objective",
                "workflow_status": "active",
                "branch_priority": "primary",
            },
        )
        record_research_node(
            self.root,
            {
                "slug": "abandoned-route",
                "kind": "analysis",
                "label": "Abandoned route",
                "parent_slug": "objective-root",
                "workflow_status": "active",
            },
        )
        set_research_tree_state(
            self.root,
            {"root_slug": "objective-root", "active_slug": "objective-root"},
        )
        branch = "research/analysis/abandoned-route"
        subprocess.run(["git", "-C", str(self.root), "switch", "-c", branch], check=True, capture_output=True)
        (self.root / "route.md").write_text("failed route\n", encoding="utf-8")
        scientific_tip = self._commit("try abandoned route")
        record_research_branch(
            self.root,
            {"node_slug": "abandoned-route", "disposition": "active"},
        )
        self._commit("record active branch provenance")
        record_research_node(
            self.root,
            {
                "slug": "abandoned-route",
                "kind": "analysis",
                "label": "Abandoned route",
                "parent_slug": "objective-root",
                "workflow_status": "closed",
                "closure_reason": "Model assumptions failed diagnostics.",
            },
        )
        archived = record_research_branch(
            self.root,
            {
                "node_slug": "abandoned-route",
                "disposition": "archived",
                "closure_reason": "Model assumptions failed diagnostics.",
            },
        )
        self.assertEqual(archived["tip_commit"], scientific_tip)
        closure_commit = self._commit("close abandoned route")
        tag = "research-closed/analysis/abandoned-route"
        subprocess.run(
            ["git", "-C", str(self.root), "tag", "-a", tag, "-m", "Model assumptions failed diagnostics."],
            check=True,
        )
        self.assertNotEqual(closure_commit, scientific_tip)

        readiness = research_tree_completion_readiness(self.root)
        reasons = {item["reason"] for item in readiness["blockers"]}
        self.assertNotIn("research_git_archive_tag_mismatch", reasons)
        self.assertNotIn("research_git_archive_ref_invalid", reasons)

    def test_analysis_attempt_pins_commit_and_rejects_sys_path_hack(self) -> None:
        scripts = self.root / "scripts" / "analyses"
        scripts.mkdir(parents=True)
        good = scripts / "model.py"
        good.write_text("from projectpkg.statistics import fit_model\n\nprint('run')\n", encoding="utf-8")
        package = self.root / "src" / "projectpkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "statistics.py").write_text("def fit_model():\n    return 1\n", encoding="utf-8")
        attempt_dir = self.root / ".research" / "analysis" / "model" / "A001"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "config.yaml").write_text("parameter: 1\n", encoding="utf-8")
        commit = self._commit("add analysis code and config")

        with connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs(
                    slug, title, analysis_mode, status, target_uncertainty, estimand,
                    unit_of_inference, primary_analysis, analysis_path, code_path,
                    freeze_commit, started_at, completed_at, created_at, updated_at, design_id
                ) VALUES (
                    'model', 'Model', 'exploratory', 'planned', 'uncertainty', 'estimand',
                    'sample', 'model', 'RESEARCH.md', 'scripts/analyses/model.py',
                    NULL, '2026-01-01T00:00:00+00:00', NULL,
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', NULL
                )
                """
            )

        (attempt_dir / "outputs").mkdir()
        result = record_analysis_attempt(
            self.root,
            {
                "analysis_slug": "model",
                "attempt_key": "A001",
                "status": "completed",
                "git_commit": commit,
                "config_path": ".research/analysis/model/A001/config.yaml",
                "output_path": ".research/analysis/model/A001/outputs",
                "reason": "First executable specification.",
            },
        )
        self.assertEqual(result["git_commit"], commit)

        bad = scripts / "bad.py"
        bad.write_text("import sys\nsys.path.append('../other')\n", encoding="utf-8")
        bad_commit = self._commit("add unsafe entrypoint")
        with connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs(
                    slug, title, analysis_mode, status, target_uncertainty, estimand,
                    unit_of_inference, primary_analysis, analysis_path, code_path,
                    freeze_commit, started_at, completed_at, created_at, updated_at, design_id
                ) VALUES (
                    'bad', 'Bad', 'exploratory', 'planned', 'uncertainty', 'estimand',
                    'sample', 'bad', 'RESEARCH.md', 'scripts/analyses/bad.py',
                    NULL, '2026-01-01T00:00:00+00:00', NULL,
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', NULL
                )
                """
            )
        bad_dir = self.root / ".research" / "analysis" / "bad" / "B001"
        bad_dir.mkdir(parents=True)
        with self.assertRaisesRegex(ResearchDbError, "sys.path"):
            record_analysis_attempt(
                self.root,
                {
                    "analysis_slug": "bad",
                    "attempt_key": "B001",
                    "status": "completed",
                    "git_commit": bad_commit,
                    "output_path": ".research/analysis/bad/B001",
                    "reason": "Unsafe legacy attempt.",
                },
            )

    def test_user_checkbox_confirmation_tracks_current_note_version(self) -> None:
        papers = self.root / "literature" / "papers"
        papers.mkdir(parents=True)
        sidecar = papers / "Paper - Wang - 2026.md"
        sidecar.write_text(
            "# Paper\n\n"
            + confirmation_control("top", checked=True)
            + "\n\n## 三句话总结\n\n内容。\n\n## 结论边界\n\n边界。\n\n"
            + confirmation_control("bottom")
            + "\n",
            encoding="utf-8",
        )
        with connect(database_path(self.root)) as connection:
            connection.execute(
                """
                INSERT INTO papers(id, title, status, sidecar_path, created_at, updated_at)
                VALUES ('P000001', 'Paper', 'active', ?, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
                """,
                (sidecar.relative_to(self.root).as_posix(),),
            )

        synced = sync_user_reading(self.root, paper_id="P000001")
        self.assertTrue(synced["papers"][0]["confirmed_current_version"])
        text = sidecar.read_text(encoding="utf-8")
        self.assertEqual(text.count("- [x] **我已阅读并确认当前版本**"), 2)

        updated = text.replace("内容。", "更新后的内容。")
        sidecar.write_text(updated, encoding="utf-8")
        invalidated = sync_user_reading(self.root, paper_id="P000001")
        self.assertEqual(invalidated["papers"][0]["action"], "invalidated")
        self.assertFalse(invalidated["papers"][0]["confirmed_current_version"])
        reset_text = sidecar.read_text(encoding="utf-8")
        self.assertEqual(reset_text.count("- [ ] **我已阅读并确认当前版本**"), 2)

        user_checked = reset_text.replace(
            "- [ ] **我已阅读并确认当前版本**",
            "- [x] **我已阅读并确认当前版本**",
            1,
        )
        sidecar.write_text(user_checked, encoding="utf-8")
        reconfirmed = sync_user_reading(self.root, paper_id="P000001")
        self.assertEqual(reconfirmed["papers"][0]["action"], "confirmed")
        status = user_reading_status(self.root, paper_id="P000001")
        self.assertTrue(status["papers"][0]["confirmed_current_version"])


if __name__ == "__main__":
    unittest.main()
