from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_cdp as cli
import browser_cdp_lifecycle as lifecycle
import browser_cdp_profiles as profiles
from browser_cdp_core import BrowserCdpError


class DedicatedProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = lifecycle.BrowserConfig(
            endpoint="http://localhost:9223",
            user_data_dir=r"C:\Users\Akira\.agent-browser\chrome-profile",
            identity="chrome-profile",
        )
        self.version = {"Browser": "Chrome/test", "webSocketDebuggerUrl": "ws://localhost:9223/browser"}

    def verified_client(self, *, directory: str | None = None, profile: str = "Default") -> MagicMock:
        client = MagicMock()
        client.__enter__.return_value.call.return_value = {"arguments": [
            "chrome.exe", "--enable-automation",
            "--user-data-dir=" + (directory or self.config.user_data_dir or ""),
            "--profile-directory=" + profile,
        ]}
        return client

    def test_no_options_preserve_default(self) -> None:
        args = cli.build_parser().parse_args(["tabs"])
        config = lifecycle.config_from_options(args.endpoint, args.user_data_dir, args.profile_directory)
        self.assertEqual(config, lifecycle.BrowserConfig())
        command = lifecycle.launch_command(config)
        self.assertIn("--remote-debugging-port=9222", command)
        self.assertIn(".agent-browser\\profile", command)

    def test_custom_launch_uses_independent_directory_port_and_quoted_arguments(self) -> None:
        config = lifecycle.config_from_options("http://localhost:9223", r"C:\Agent Data\O'Brien", "Profile 2")
        command = lifecycle.launch_command(config)
        self.assertIn("--remote-debugging-port=9223", command)
        self.assertIn("'C:\\Agent Data\\O''Brien'", command)
        self.assertIn('\'"--profile-directory=Profile 2"\'', command)
        self.assertIn("('--user-data-dir", command.replace('"', ''))
        self.assertIn("--enable-automation", command)
        self.assertNotIn("--remote-debugging-port=9222", command)

    def test_custom_directory_cannot_silently_use_default_port(self) -> None:
        for endpoint in (None, "http://localhost:9222", "http://127.0.0.1:9222"):
            with self.subTest(endpoint=endpoint), self.assertRaises(BrowserCdpError):
                lifecycle.config_from_options(endpoint, self.config.user_data_dir, None)

    def test_daily_and_default_agent_directories_are_excluded(self) -> None:
        for directory in (
            r"C:\Users\Akira\AppData\Local\Google\Chrome\User Data",
            r"C:\Users\Akira\AppData\Local\Google\Chrome\User Data\Profile 7",
            r"C:\Users\Akira\.agent-browser\profile",
            r"C:\Users\Akira\.agent-browser\profile\nested",
            r"C:\Users\Akira\.agent-browser\profile.",
        ):
            with self.subTest(directory=directory), self.assertRaises(BrowserCdpError):
                lifecycle.config_from_options("http://localhost:9223", directory, None)

    def test_remote_endpoint_is_attach_only(self) -> None:
        with self.assertRaises(BrowserCdpError):
            lifecycle.launch_command(lifecycle.BrowserConfig(endpoint="https://remote.example:9223", identity=None))

    def test_alternate_port_without_directory_does_not_launch_default_profile(self) -> None:
        with self.assertRaises(BrowserCdpError):
            lifecycle.launch_command(lifecycle.BrowserConfig(endpoint="http://localhost:9223", identity=None))

    def test_invalid_endpoint_or_profile_directory_is_rejected(self) -> None:
        for endpoint, profile in (("http://localhost:bad", "Default"),
                                  ("http://localhost:9223/json/list", "Default"),
                                  ("http://user:secret@localhost:9223", "Default"),
                                  ("http://localhost:9223", "../Profile 7")):
            with self.subTest(endpoint=endpoint, profile=profile), self.assertRaises(BrowserCdpError):
                lifecycle.config_from_options(endpoint, self.config.user_data_dir, profile)

    def test_empty_explicit_options_and_invalid_windows_paths_are_rejected(self) -> None:
        for endpoint, profile in (("", "Default"), ("http://localhost:9223\n", "Default"),
                                  ("http://localhost:9223", ""), ("http://localhost:9223", "Default.")):
            with self.subTest(endpoint=endpoint, profile=profile), self.assertRaises(BrowserCdpError):
                lifecycle.config_from_options(endpoint, self.config.user_data_dir, profile)
        for directory in ("C:\\", r"C:\Agent\name.", r"C:\Agent\name*", r"C:\Agent "):
            with self.subTest(directory=directory), self.assertRaises(BrowserCdpError):
                lifecycle.config_from_options("http://localhost:9223", directory, None)

    def test_verified_existing_instance_is_reused_without_launch(self) -> None:
        with patch.object(lifecycle, "probe_version", return_value=self.version), \
             patch.object(lifecycle, "browser_client", return_value=self.verified_client()), \
             patch.object(lifecycle, "launch_windows_agent_chrome") as launch:
            result = lifecycle.ensure_browser(self.config, timeout=1)
        launch.assert_not_called()
        self.assertTrue(result["reused"])
        self.assertTrue(result["profileVerified"])

    def test_mismatch_refuses_page_access_without_relaunch(self) -> None:
        for directory, profile in ((r"C:\wrong", "Default"), (None, "Profile 7")):
            with self.subTest(directory=directory, profile=profile), \
                 patch.object(lifecycle, "probe_version", return_value=self.version), \
                 patch.object(lifecycle, "browser_client", return_value=self.verified_client(directory=directory, profile=profile)), \
                 patch.object(lifecycle, "launch_windows_agent_chrome") as launch, \
                 patch.object(lifecycle, "list_targets") as targets, self.assertRaises(BrowserCdpError):
                lifecycle.ensure_then_targets(self.config, timeout=1)
            launch.assert_not_called()
            targets.assert_not_called()

    def test_unverifiable_profile_is_reported_by_status_and_blocked_for_actions(self) -> None:
        with patch.object(lifecycle, "probe_version", return_value=self.version), \
             patch.object(lifecycle, "browser_client", side_effect=BrowserCdpError("not enabled")), \
             patch.object(lifecycle, "launch_windows_agent_chrome") as launch:
            status = lifecycle.browser_status(self.config, timeout=1)
            self.assertTrue(status["connected"])
            self.assertFalse(status["profileVerified"])
            self.assertIn("--enable-automation", status["profileError"])
            with self.assertRaises(BrowserCdpError):
                lifecycle.ensure_browser(self.config, timeout=1)
        launch.assert_not_called()

    def test_status_does_not_launch_when_disconnected(self) -> None:
        with patch.object(lifecycle, "probe_version", return_value=None), \
             patch.object(lifecycle, "launch_windows_agent_chrome") as launch:
            self.assertFalse(lifecycle.browser_status(self.config, timeout=1)["connected"])
        launch.assert_not_called()

    def test_default_legacy_instance_remains_usable_without_verification(self) -> None:
        with patch.object(lifecycle, "probe_version", return_value=self.version), \
             patch.object(lifecycle, "browser_client") as client:
            result = lifecycle.ensure_browser(lifecycle.BrowserConfig(), timeout=1)
        self.assertEqual(result["profileIdentity"], "agent-browser")
        self.assertFalse(result["profileVerified"])
        client.assert_not_called()

    def test_new_instance_is_verified_after_launch(self) -> None:
        with patch.object(lifecycle, "probe_version", side_effect=[None, self.version]), \
             patch.object(lifecycle, "browser_client", return_value=self.verified_client()), \
             patch.object(lifecycle, "launch_windows_agent_chrome", return_value="chrome.exe") as launch:
            result = lifecycle.ensure_browser(self.config, timeout=1)
        launch.assert_called_once_with(self.config)
        self.assertFalse(result["reused"])
        self.assertTrue(result["profileVerified"])


class NamedProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "profiles.toml"
        self.config = lifecycle.BrowserConfig(
            endpoint="http://localhost:9223", user_data_dir=r"C:\Agent Data\ChatGPT",
            identity="chatgpt",
        )

    def test_saved_configuration_roundtrips_paths_and_is_selected_by_name(self) -> None:
        profiles.save_profile("chatgpt", self.config, self.path)
        self.assertEqual(profiles.resolve_profile("chatgpt", self.path, None, None, None), self.config)
        self.assertFalse(self.path.with_name("profiles.toml.lock").exists())

    def test_unknown_name_does_not_fall_back_or_create_configuration(self) -> None:
        with self.assertRaises(BrowserCdpError):
            profiles.resolve_profile("missing", self.path, None, None, None)
        self.assertFalse(self.path.exists())

    def test_no_name_or_builtin_name_ignores_missing_or_corrupt_file(self) -> None:
        self.path.write_text("broken [ configuration", encoding="utf-8")
        for name in (None, "agent-browser"):
            self.assertEqual(profiles.resolve_profile(name, self.path, None, None, None), lifecycle.BrowserConfig())

    def test_named_profile_rejects_partial_overrides(self) -> None:
        with self.assertRaises(BrowserCdpError):
            profiles.resolve_profile("chatgpt", self.path, "http://localhost:9224", None, None)

    def test_builtin_and_invalid_names_cannot_be_saved(self) -> None:
        for name in ("agent-browser", "Profile 7", "../../profile", "ChatGPT"):
            with self.subTest(name=name), self.assertRaises(BrowserCdpError):
                profiles.save_profile(name, self.config, self.path)
        self.assertFalse(self.path.exists())

    def test_duplicate_names_ports_or_directories_preserve_existing_file(self) -> None:
        profiles.save_profile("chatgpt", self.config, self.path)
        original = self.path.read_bytes()
        for name, config in (
            ("chatgpt", lifecycle.BrowserConfig(endpoint="http://localhost:9224", user_data_dir=r"C:\Agent\Second")),
            ("second", lifecycle.BrowserConfig(endpoint="http://127.0.0.1:9223", user_data_dir=r"C:\Agent\Second")),
            ("second", lifecycle.BrowserConfig(endpoint="http://localhost:9224", user_data_dir=r"c:/agent data/chatgpt")),
            ("second", lifecycle.BrowserConfig(endpoint="http://localhost:9224", user_data_dir=r"C:\Agent Data\ChatGPT\nested")),
            ("second", lifecycle.BrowserConfig(endpoint="http://localhost:9224", user_data_dir=r"C:\Agent Data")),
        ):
            with self.subTest(name=name, config=config), self.assertRaises(BrowserCdpError):
                profiles.save_profile(name, config, self.path)
            self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_schema_is_rejected_without_rewriting(self) -> None:
        for content in ("schema = 2\n[profiles]\n", "schema = true\n[profiles]\n",
                        "schema = 1\n[profiles.chatgpt]\nendpoint = 9223\nuser_data_dir = 'C:\\Agent'\n"):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(BrowserCdpError):
                    profiles.load_profiles(self.path)
                self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_existing_lock_prevents_writes_and_is_preserved(self) -> None:
        lock = self.path.with_name("profiles.toml.lock")
        lock.write_text("another process", encoding="utf-8")
        with self.assertRaises(BrowserCdpError):
            profiles.save_profile("chatgpt", self.config, self.path)
        self.assertFalse(self.path.exists())
        self.assertTrue(lock.exists())

    def test_failed_atomic_replace_preserves_file_and_cleans_lock(self) -> None:
        profiles.save_profile("chatgpt", self.config, self.path)
        original = self.path.read_bytes()
        with patch.object(profiles.os, "replace", side_effect=OSError("write failed")), self.assertRaises(BrowserCdpError):
            profiles.save_profile("second", lifecycle.BrowserConfig(
                endpoint="http://localhost:9224", user_data_dir=r"C:\Agent\Second"), self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_cli_save_and_list_do_not_connect_or_launch(self) -> None:
        commands = [
            ["--config", str(self.path), "--endpoint", self.config.endpoint,
             "--user-data-dir", self.config.user_data_dir, "profile-save", "chatgpt"],
            ["--config", str(self.path), "profiles"],
        ]
        with patch.object(lifecycle, "probe_version") as probe, patch.object(lifecycle, "launch_windows_agent_chrome") as launch:
            for command in commands:
                with patch.object(sys, "argv", ["browser_cdp.py", *command]), redirect_stdout(StringIO()):
                    self.assertEqual(cli.main(), 0)
        probe.assert_not_called()
        launch.assert_not_called()

    def test_cli_propagates_named_configuration_to_page_commands(self) -> None:
        profiles.save_profile("chatgpt", self.config, self.path)
        with patch.object(sys, "argv", ["browser_cdp.py", "--config", str(self.path), "--profile", "chatgpt", "tabs"]), \
             patch.object(cli, "ensure_then_targets", return_value=[]) as targets, redirect_stdout(StringIO()):
            self.assertEqual(cli.main(), 0)
        targets.assert_called_once_with(self.config, timeout=15.0)


if __name__ == "__main__":
    unittest.main()
