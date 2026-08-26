from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from research_db import _load_json_object, build_parser, bundle_path  # noqa: E402
from research_db_core import init_database  # noqa: E402


class ResearchDbCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
        init_database(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_bundle_defaults_live_under_research_directory(self) -> None:
        expected = self.root / ".research" / "bundles" / "reconstruction.json"
        expected.write_text(json.dumps({"paper_id": "P000001"}), encoding="utf-8")

        self.assertEqual(bundle_path(self.root, "ingest-reading", None), expected)
        self.assertEqual(
            _load_json_object(self.root, "ingest-reading", None),
            {"paper_id": "P000001"},
        )

    def test_explicit_relative_bundle_path_is_project_relative(self) -> None:
        custom = self.root / ".research" / "bundles" / "custom.json"
        custom.write_text(json.dumps({"ok": True}), encoding="utf-8")

        self.assertEqual(
            bundle_path(self.root, "ingest-reading", ".research/bundles/custom.json"),
            custom,
        )

    def test_bundle_argument_is_optional(self) -> None:
        args = build_parser().parse_args(
            ["--project", str(self.root), "ingest-critical"]
        )
        self.assertIsNone(args.bundle)

        search_args = build_parser().parse_args(
            ["--project", str(self.root), "record-search"]
        )
        self.assertIsNone(search_args.bundle)

    def test_read_query_commands_are_exposed(self) -> None:
        search_args = build_parser().parse_args(
            ["--project", str(self.root), "search", "Blautia", "--entity-type", "claim"]
        )
        self.assertEqual(search_args.entity_type, ["claim"])

        issue_args = build_parser().parse_args(
            [
                "--project",
                str(self.root),
                "issues",
                "--paper",
                "P000001",
                "--severity",
                "major",
            ]
        )
        self.assertEqual(issue_args.paper, "P000001")
        self.assertEqual(issue_args.severity, "major")

        related_args = build_parser().parse_args(
            ["--project", str(self.root), "related", "P000001"]
        )
        self.assertEqual(related_args.paper_id, "P000001")

    def test_candidate_queue_filters_are_exposed(self) -> None:
        args = build_parser().parse_args(
            [
                "--project",
                str(self.root),
                "candidates",
                "--relevance",
                "relevant",
                "--acquisition",
                "queued",
                "--priority",
                "core",
            ]
        )
        self.assertEqual(args.relevance, "relevant")
        self.assertEqual(args.acquisition, "queued")
        self.assertEqual(args.priority, "core")


if __name__ == "__main__":
    unittest.main()
