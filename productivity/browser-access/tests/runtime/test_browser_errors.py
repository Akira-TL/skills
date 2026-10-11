"""Stable error contracts for callers, including interleaved CDP exceptions."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from browser_cdp_core import BrowserCdpError, CdpClient, select_target
from browser_cdp import build_parser


class ErrorTests(unittest.TestCase):
    def test_no_target_and_ambiguous_have_distinct_codes(self):
        with self.assertRaises(BrowserCdpError) as caught:
            select_target([], None)
        self.assertEqual(caught.exception.code, "TARGET_NOT_FOUND")
        pages = [{"id": str(i), "type": "page", "url": "https://example.org",
                  "webSocketDebuggerUrl": "ws://example.org"} for i in range(2)]
        with self.assertRaises(BrowserCdpError) as caught:
            select_target(pages, None)
        self.assertEqual(caught.exception.code, "TARGET_AMBIGUOUS")

    def test_parser_errors_are_structured(self):
        with self.assertRaises(BrowserCdpError) as caught:
            build_parser().parse_args(["click"])
        self.assertEqual(caught.exception.as_dict()["error_code"], "INVALID_ARGUMENT")

    def test_javascript_guard_survives_cdp_exception(self):
        client = CdpClient("ws://unused")
        failure = {"error_code": "ELEMENT_OCCLUDED", "message": "blocked", "context": {"selector": "#x"}}
        client.call = lambda *args: {"exceptionDetails": {"exception": {
            "description": "Error: BROWSER_ERROR:" + json.dumps(failure) + "\n at eval"}}}
        with self.assertRaises(BrowserCdpError) as caught:
            client.evaluate("test")
        self.assertEqual(caught.exception.code, "ELEMENT_OCCLUDED")
        self.assertEqual(caught.exception.context, {"selector": "#x"})

    def test_plain_javascript_exception_is_not_protocol_error(self):
        client = CdpClient("ws://unused")
        client.call = lambda *args: {"exceptionDetails": {"text": "SyntaxError"}}
        with self.assertRaises(BrowserCdpError) as caught:
            client.evaluate("test")
        self.assertEqual(caught.exception.code, "JS_EXCEPTION")
