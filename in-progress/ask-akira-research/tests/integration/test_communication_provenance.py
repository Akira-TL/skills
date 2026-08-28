from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db_core import init_database  # noqa: E402
from research_db_ops.communication import record_communication  # noqa: E402
from research_db_ops.completion import validate_completion  # noqa: E402
from research_db_ops.downstream import record_dataset  # noqa: E402


class CommunicationProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text(
            "# Research\n\n## Current State\n\n这是中文科研项目状态，用于验证传播产物与冻结证据之间的溯源关系。当前研究还需要保持结论强度、统计不确定性、实验设计边界与传播表述一致，避免传播阶段产生新的科学事实或因果升级。\n",
            encoding="utf-8",
        )
        init_database(self.root)
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "research@example.test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Research Test"], check=True)

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

    def _write_communication(self, text: str = "三组均值存在统计学差异，因果解释仍受研究设计信息限制。") -> None:
        path = self.root / "communication" / "RESULTS.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# 结果\n\n" + text + "\n", encoding="utf-8")

    def _record_completed(self, source_commit: str) -> None:
        record_communication(
            self.root,
            {
                "slug": "main-results",
                "title": "主要结果传播稿",
                "purpose": "形成面向科研读者的结果传播稿",
                "audience": "科研读者",
                "source_commit": source_commit,
                "status": "completed",
                "artifacts": [
                    {
                        "role": "results",
                        "path": "communication/RESULTS.md",
                        "timing_role": "derived_output",
                    }
                ],
            },
        )

    def test_completion_rejects_tracked_communication_without_product_record(self) -> None:
        self._commit("RESEARCH: establish state")
        self._write_communication()
        self._commit("DOCS: add unregistered communication")
        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        reasons = {item["reason"] for item in result["communication"]["blockers"]}
        self.assertIn("communication_artifacts_unregistered", reasons)
        self.assertIn("communication_assets_present_without_product_record", reasons)

    def test_completed_communication_is_tied_to_precommunication_source(self) -> None:
        source_commit = self._commit("RESEARCH: freeze scientific source")
        self._write_communication()
        self._record_completed(source_commit)
        self._commit("DOCS: record communication")
        result = validate_completion(self.root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(result["communication"]["ready"])
        self.assertIn("communication/RESULTS.md", result["git"]["canonical_paths"])

    def test_completion_rejects_scientific_source_change_after_communication_freeze(self) -> None:
        data_dir = self.root / "data" / "example"
        data_dir.mkdir(parents=True)
        (data_dir / "README.md").write_text("# 数据\n\n每一行为一个分析记录。\n", encoding="utf-8")
        raw = data_dir / "raw.csv"
        raw.write_text("id,y\n1,1\n", encoding="utf-8")
        record_dataset(
            self.root,
            {
                "slug": "example-data",
                "title": "示例数据",
                "source": "测试来源",
                "received_at": "2026-08-28T00:00:00+00:00",
                "unit_of_inference": "分析记录",
                "provenance_path": "data/example/README.md",
                "artifacts": [{"role": "raw", "location": "data/example/raw.csv"}],
            },
        )
        source_commit = self._commit("RESEARCH: freeze scientific source")
        raw.write_text("id,y\n1,2\n", encoding="utf-8")
        self._write_communication()
        self._record_completed(source_commit)
        self._commit("DOCS: communicate after science changed")
        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        reasons = {item["reason"] for item in result["communication"]["blockers"]}
        self.assertIn("scientific_source_changed_after_communication_freeze", reasons)

    def test_chinese_communication_rejects_bare_mature_english_terms(self) -> None:
        source_commit = self._commit("RESEARCH: freeze scientific source")
        self._write_communication("当前 treatment 的 outcome analysis 仍属于 exploratory 结果。")
        self._record_completed(source_commit)
        self._commit("DOCS: add mixed-language communication")
        result = validate_completion(self.root)
        self.assertFalse(result["ok"])
        blockers = result["academic_language"]["blockers"]
        self.assertTrue(any(item["reason"] == "bare_english_term_in_chinese_communication" for item in blockers))


if __name__ == "__main__":
    unittest.main()
