from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_cdp as cli
from browser_cdp_core import BrowserCdpError
from browser_cdp_lifecycle import BrowserConfig


class GuardedCallTests(unittest.TestCase):
    def arguments(self, *, browser_scope: bool = False) -> argparse.Namespace:
        args = cli.build_parser().parse_args([
            "call", "Input.insertText", "--params", '{"text":"继续"}',
            "--guard", "document.activeElement.innerText.trim() === ''",
            "--scope", "browser" if browser_scope else "page",
        ])
        args.browser = BrowserConfig()
        return args

    def invoke(self, guard_result: object) -> MagicMock:
        client = MagicMock()
        client.evaluate.return_value = guard_result
        context = MagicMock()
        context.__enter__.return_value = client
        with patch.object(cli, "selected_target", return_value={"id": "page-a", "title": "ChatGPT", "url": "https://chatgpt.com/"}), \
             patch.object(cli, "locked_page", return_value=context):
            try:
                cli.command_call(self.arguments())
            except BrowserCdpError:
                client.call.assert_not_called()
                raise
        return client

    def test_false_or_non_boolean_guard_sends_no_input(self) -> None:
        for result in (False, None, "true", 1, []):
            with self.subTest(result=result), self.assertRaises(BrowserCdpError):
                self.invoke(result)

    def test_true_guard_performs_only_the_explicit_call(self) -> None:
        client = self.invoke(True)
        client.call.assert_called_once_with("Input.insertText", {"text": "继续"})
        client.evaluate.assert_called_once_with(
            "document.activeElement.innerText.trim() === ''", await_promise=True,
        )

    def test_page_guard_cannot_be_used_for_browser_scope(self) -> None:
        with patch.object(cli, "browser_client") as client, \
             patch.object(cli, "ensure_browser") as ensure, self.assertRaises(BrowserCdpError):
            cli.command_call(self.arguments(browser_scope=True))
        client.assert_not_called()
        ensure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
