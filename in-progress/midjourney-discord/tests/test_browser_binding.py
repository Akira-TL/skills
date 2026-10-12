"""用公开 BrowserSession 与模拟协议端验证 Discord 业务适配，不发送真实频道消息。"""
import json
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "productivity/browser-access/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mj_discord_core as core
from browser_cdp_core import BrowserCdpError

URL = "https://discord.com/channels/1/2"
CLI = REPOSITORY / "productivity/browser-access/scripts/browser_cdp.py"


class Peer:
    def __init__(self):
        self.url = URL
        self.loader = "doc-one"
        self.connections = 0
        self.closed = False
        self.actions = []
        self._events = []

    def __enter__(self):
        self.connections += 1
        return self

    def __exit__(self, *_):
        self.closed = True

    def call(self, method, params=None):
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame", "loaderId": self.loader, "url": self.url}}}
        if method.startswith("Input."):
            self.actions.append(method)
        return {}

    def evaluate(self, expression, **_options):
        if expression == "({url:location.href,title:document.title})":
            return {"url": self.url, "title": "channel"}
        if "composer:" in expression:
            return {"href": self.url, "title": "channel", "composer": "Message"}
        return 42


class BrowserBindingTests(unittest.TestCase):
    def setUp(self):
        self.peer = Peer()
        self.args = Namespace(channel_url=URL, endpoint=None, timeout=10, target=None)
        self.targets = [{"id": "one", "url": URL, "title": "channel", "type": "page",
                         "webSocketDebuggerUrl": "ws://unused"},
                        {"id": "two", "url": "https://discord.com/channels/3/4", "title": "other",
                         "type": "page", "webSocketDebuggerUrl": "ws://unused"}]
        def cli_result(command, **_options):
            if command[-1] == "status":
                return Namespace(returncode=0, stdout='{"connected":true,"endpoint":"http://unused"}', stderr="")
            if command[-1] == "tabs":
                return Namespace(returncode=0, stdout=json.dumps({"pages": self.targets}), stderr="")
            raise AssertionError("页面动作不应再启动 browser-access 子进程")
        patches = [patch.object(core, "resolve_browser_cli", return_value=CLI),
                   patch.object(core.shutil, "which", return_value="uv"),
                   patch.object(core.subprocess, "run", side_effect=cli_result),
                   patch("browser_runtime.session.list_targets", side_effect=lambda *_a, **_k: self.targets),
                   patch("browser_runtime.session.page_client", return_value=self.peer)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_business_reads_and_keyboard_action_share_one_locked_connection(self):
        with core.browser_operations(self.args):
            target = core.resolve_target(self.args)
            for _ in range(20):
                self.assertEqual(core.eval_js(self.args, target["id"], "42"), 42)
            core.insert_text(self.args, target["id"], "fixture text")
            self.assertEqual(core.resolve_target(self.args)["id"], "one")
        self.assertEqual(self.peer.connections, 1)
        self.assertEqual(self.peer.actions, ["Input.insertText"])
        self.assertTrue(self.peer.closed)

    def test_navigation_then_return_does_not_restore_permission_to_send(self):
        with self.assertRaises(core.MjDiscordError) as caught:
            with core.browser_operations(self.args):
                core.resolve_target(self.args)
                self.peer.url = self.targets[0]["url"] = self.targets[1]["url"]
                with self.assertRaises(BrowserCdpError):
                    core.eval_js(self.args, "one", "42")
                self.peer.url = self.targets[0]["url"] = URL
                core.insert_text(self.args, "one", "must not send")
        self.assertEqual(caught.exception.code, "TARGET_LOCK_VIOLATION")
        self.assertEqual(self.peer.actions, [])
        self.assertTrue(self.peer.closed)

    def test_reload_same_url_is_reported_as_document_change(self):
        with self.assertRaises(core.MjDiscordError) as caught:
            with core.browser_operations(self.args):
                core.resolve_target(self.args)
                self.peer.loader = "doc-two"
                core.insert_text(self.args, "one", "must not send")
        self.assertEqual(caught.exception.code, "NAVIGATION_DETECTED")
        self.assertEqual(caught.exception.as_dict()["error_code"], "NAVIGATION_DETECTED")
        self.assertEqual(self.peer.actions, [])

    def test_closed_selected_page_does_not_select_the_other_channel(self):
        with self.assertRaises(core.MjDiscordError) as caught:
            with core.browser_operations(self.args):
                core.resolve_target(self.args)
                self.targets.pop(0)
                core.insert_text(self.args, "one", "must not send")
        self.assertEqual(caught.exception.code, "TARGET_LOCK_VIOLATION")
        self.assertEqual(self.peer.connections, 1)
        self.assertEqual(self.peer.actions, [])

    def test_browser_error_code_and_context_survive_cli_boundary(self):
        payload = {"ok": False, "error_code": "ELEMENT_OCCLUDED", "message": "blocked",
                   "context": {"selector": "#composer"}}
        with patch.object(core.subprocess, "run", return_value=Namespace(returncode=2, stdout=json.dumps(payload), stderr="")):
            with self.assertRaises(core.MjDiscordError) as caught:
                core.run_browser(self.args, "tabs")
        self.assertEqual(caught.exception.as_dict()["context"], {"selector": "#composer"})
        self.assertEqual(caught.exception.code, "ELEMENT_OCCLUDED")

    def test_missing_public_api_fails_before_any_page_connection(self):
        with patch.object(core, "resolve_browser_cli", return_value=Path("/missing/browser_cdp.py")):
            with self.assertRaises(core.MjDiscordError) as caught:
                with core.browser_operations(self.args):
                    core.resolve_target(self.args)
        self.assertEqual(caught.exception.code, "BROWSER_CAPABILITY_MISSING")
        self.assertEqual(self.peer.connections, 0)
        self.assertEqual(self.peer.actions, [])

    def test_legacy_page_operations_use_public_session_parameters(self):
        class RecordingSession:
            def __init__(self):
                self.calls = []
            def execute(self, op, **options):
                self.calls.append((op, options))
                return {"target": {"id": "one"}}
        page = RecordingSession()
        core.session_operation(page, ("click", "--target", "one", "#submit", "--allow-submit"))
        core.session_operation(page, ("type", "--target", "one", "#editor", "fixture"))
        core.session_operation(page, ("upload", "--target", "one", "input[type=file]", "a.png", "b.png"))
        self.assertEqual(page.calls, [("click", {"selector": "#submit", "allow_submit": True}),
                                      ("type", {"selector": "#editor", "value": "fixture"}),
                                      ("upload", {"selector": "input[type=file]", "files": ["a.png", "b.png"]})])


if __name__ == "__main__":
    unittest.main()
