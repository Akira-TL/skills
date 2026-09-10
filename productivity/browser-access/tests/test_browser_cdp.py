from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browser_cdp_core.py"
SPEC = importlib.util.spec_from_file_location("browser_cdp_core", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SCRIPT}")
BROWSER_CDP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BROWSER_CDP
SPEC.loader.exec_module(BROWSER_CDP)


class NetworkSummaryTests(unittest.TestCase):
    def test_summarizes_only_safe_response_metadata(self) -> None:
        events = [
            {
                "method": "Network.requestWillBeSent",
                "params": {
                    "requestId": "r1",
                    "type": "Document",
                    "request": {
                        "url": "https://example.org/paper.pdf",
                        "method": "GET",
                        "headers": {"Authorization": "Bearer secret"},
                    },
                },
            },
            {
                "method": "Network.responseReceived",
                "params": {
                    "requestId": "r1",
                    "type": "Document",
                    "response": {
                        "url": "https://example.org/paper.pdf",
                        "status": 200,
                        "mimeType": "application/pdf",
                        "headers": {
                            "Content-Type": "application/pdf",
                            "Content-Disposition": "inline; filename=paper.pdf",
                            "Set-Cookie": "session=secret",
                        },
                    },
                },
            },
        ]
        records = BROWSER_CDP.summarize_network_events(events)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["contentType"], "application/pdf")
        self.assertEqual(records[0]["contentDisposition"], "inline; filename=paper.pdf")
        self.assertNotIn("headers", records[0])
        self.assertNotIn("Authorization", str(records[0]))
        self.assertNotIn("Set-Cookie", str(records[0]))

    def test_url_filter_excludes_unrelated_requests(self) -> None:
        events = [
            {
                "method": "Network.requestWillBeSent",
                "params": {
                    "requestId": "r1",
                    "type": "Script",
                    "request": {"url": "https://example.org/app.js", "method": "GET"},
                },
            }
        ]
        self.assertEqual(BROWSER_CDP.summarize_network_events(events, url_contains="paper"), [])


class SelectTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.targets = [
            {
                "id": "worker-1",
                "type": "service_worker",
                "title": "worker",
                "url": "https://example.org/sw.js",
            },
            {
                "id": "page-a123",
                "type": "page",
                "title": "Web of Science",
                "url": "https://www.webofscience.com/wos/woscc/summary/abc",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/page-a123",
            },
            {
                "id": "page-b456",
                "type": "page",
                "title": "PubMed",
                "url": "https://pubmed.ncbi.nlm.nih.gov/",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/page-b456",
            },
        ]

    def test_filters_non_page_targets(self) -> None:
        pages = BROWSER_CDP.page_targets(self.targets)
        self.assertEqual([item["id"] for item in pages], ["page-a123", "page-b456"])

    def test_selector_matches_unique_id_prefix(self) -> None:
        target = BROWSER_CDP.select_target(self.targets, "page-a")
        self.assertEqual(target["id"], "page-a123")

    def test_selector_matches_title_or_url_case_insensitively(self) -> None:
        self.assertEqual(BROWSER_CDP.select_target(self.targets, "SCIENCE")["id"], "page-a123")
        self.assertEqual(BROWSER_CDP.select_target(self.targets, "ncbi.nlm")["id"], "page-b456")

    def test_ambiguous_selector_fails_closed(self) -> None:
        with self.assertRaises(BROWSER_CDP.TargetSelectionError):
            BROWSER_CDP.select_target(self.targets, "https")

    def test_no_selector_uses_only_meaningful_page(self) -> None:
        targets = [
            {
                "id": "blank",
                "type": "page",
                "title": "New Tab",
                "url": "chrome://newtab/",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/blank",
            },
            self.targets[1],
        ]
        self.assertEqual(BROWSER_CDP.select_target(targets, None)["id"], "page-a123")

    def test_no_selector_with_multiple_meaningful_pages_fails_closed(self) -> None:
        with self.assertRaises(BROWSER_CDP.TargetSelectionError):
            BROWSER_CDP.select_target(self.targets, None)


if __name__ == "__main__":
    unittest.main()
