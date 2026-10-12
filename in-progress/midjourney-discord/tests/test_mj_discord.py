from __future__ import annotations

import importlib.util
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mj_discord.py"
SPEC = importlib.util.spec_from_file_location("mj_discord", MODULE_PATH)
assert SPEC and SPEC.loader
MJ = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MJ)

import mj_discord_media as MEDIA
import mj_discord_core as CORE


class MjDiscordPureTests(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(
            MJ.normalize_url("https://discord.com/channels/1/2/?x=1"),
            "https://discord.com/channels/1/2",
        )

    def test_channel_url_rejects_other_origins_and_incomplete_paths(self):
        for url in ("https://discord.com.evil/channels/1/2", "http://discord.com/channels/1/2",
                    "https://discord.com/channels/1", "https://discord.com/channels/@me",
                    "https://user@discord.com/channels/1/2", "https://discord.com/channels/1/2/3"):
            with self.subTest(url=url), self.assertRaises(CORE.MjDiscordError):
                CORE.normalize_url(url)
        self.assertEqual(CORE.normalize_url("https://discord.com/channels/@me/123#message"),
                         "https://discord.com/channels/@me/123")

    def test_discovery_lists_open_channels_without_selecting_a_page(self):
        tabs = [{"id": "one", "url": "https://discord.com/channels/1/2", "title": "first"},
                {"id": "two", "url": "https://discord.com/channels/3/4?view=chat", "title": "second"},
                {"id": "other", "url": "https://example.com/", "title": "other"}]
        args = Namespace(endpoint=None, timeout=10)
        with patch.object(CORE, "list_tabs", return_value=tabs), patch.object(CORE, "eval_js") as evaluate:
            result = CORE.discover_channels(args)
        self.assertEqual([item["target_id"] for item in result["channels"]], ["one", "two"])
        evaluate.assert_not_called()
        self.assertFalse(hasattr(args, "_locked_target"))

    def test_same_channel_tabs_require_exact_target_id(self):
        args = Namespace(channel_url="https://discord.com/channels/1/2", target=None)
        pages = [{"target_id": name, "channel_url": args.channel_url,
                  "page_url": args.channel_url, "title": name} for name in ("one", "two")]
        with patch.object(CORE, "discover_channels", return_value={"channels": pages}):
            with self.assertRaises(CORE.MjDiscordError):
                CORE.resolve_target(args)
            args.target = "two"
            with patch.object(CORE, "eval_js", return_value={"href": args.channel_url, "composer": "Message"}):
                self.assertEqual(CORE.resolve_target(args)["id"], "two")
                self.assertEqual(args._locked_url, args.channel_url)
            args.target = "tw"
            with self.assertRaises(CORE.MjDiscordError):
                CORE.resolve_target(args)

    def test_discovery_parser_needs_no_channel_and_adds_no_named_profile(self):
        args = MJ.build_parser().parse_args(["channels"])
        self.assertEqual(args.subcommand, "channels")
        self.assertFalse(hasattr(args, "profile"))

    def test_page_action_passes_exact_observed_url_to_browser_access(self):
        args = Namespace(endpoint=None, timeout=10, _locked_target="one",
                         _locked_url="https://discord.com/channels/1/2?view=chat")
        process = Namespace(returncode=0, stdout='{"value":true}', stderr="")
        with patch.object(CORE, "resolve_browser_cli", return_value=Path("/test/browser_cdp.py")), \
             patch.object(CORE.shutil, "which", return_value="uv"), \
             patch.object(CORE.subprocess, "run", return_value=process) as run:
            self.assertTrue(CORE.eval_js(args, "one", "true"))
            command = run.call_args.args[0]
            self.assertEqual(command[-2:], ["--expected-url", args._locked_url])
            self.assertNotIn("--profile", command)
            self.assertNotIn("--endpoint", command)
            with self.assertRaises(CORE.MjDiscordError):
                CORE.eval_js(args, "two", "true")
            self.assertEqual(run.call_count, 1)

    def test_parse_waiting(self):
        self.assertEqual(MJ.parse_job_status("foo (Waiting to start)"), ("waiting", None))

    def test_parse_progress(self):
        self.assertEqual(MJ.parse_job_status("foo (67%) (fast)"), ("running", 67))

    def test_parse_completed(self):
        self.assertEqual(
            MJ.parse_job_status("foo (Open on website for full quality)"),
            ("completed", 100),
        )

    def test_parse_upscaled_completed(self):
        self.assertEqual(
            MJ.parse_job_status("prompt - Upscaled (Subtle) by @user"),
            ("completed", 100),
        )

    def test_find_message_prefers_latest(self):
        messages = [
            {"id": "a", "text": "same", "buttons": ["U1"]},
            {"id": "b", "text": "same", "buttons": ["U1"]},
        ]
        self.assertEqual(
            MJ.find_message(messages, contains="same", require_button="U1")["id"],
            "b",
        )

    def test_find_message_by_id(self):
        messages = [
            {"id": "a", "text": "one", "buttons": []},
            {"id": "b", "text": "two", "buttons": ["V1"]},
        ]
        self.assertEqual(MJ.find_message(messages, message_id="b")["text"], "two")

    def test_reroll_alias(self):
        self.assertEqual(MJ.canonical_action_label("🔄"), "Reroll")
        self.assertEqual(MJ.canonical_action_label("refresh"), "Reroll")

    def test_prompt_signature_grid(self):
        text = (
            "Midjourney Bot\n"
            "single matte white ceramic sphere --ar 1:1 --v 8.2 - @elaine "
            "(Open on website for full quality)"
        )
        self.assertEqual(
            MJ.prompt_signature(text),
            "single matte white ceramic sphere --ar 1:1 --v 8.2",
        )

    def test_prompt_signature_image_prompt_strips_urls(self):
        text = (
            "Midjourney Bot\n"
            "https://s.mj.run/abc https://s.mj.run/def "
            "a clean abstract icon --ar 1:1 --s 750 --v 8.2 - @elaine "
            "(Open on website for full quality)"
        )
        self.assertEqual(
            MJ.prompt_signature(text),
            "a clean abstract icon --ar 1:1 --s 750 --v 8.2",
        )

    def test_prompt_signature_variation(self):
        text = (
            "Midjourney Bot\n"
            "single matte white ceramic sphere --ar 1:1 --v 8.2 - Variations (Subtle) by @elaine"
        )
        self.assertEqual(
            MJ.prompt_signature(text),
            "single matte white ceramic sphere --ar 1:1 --v 8.2",
        )

    def test_extract_prompt_uses_latest_child_in_group(self):
        text = (
            "brass torus --ar 1:1 --v 8.2 - @elaine (Open on website for full quality)\n"
            "copper torus --ar 1:1 - Remix (Subtle) by @elaine "
            "(Open on website for full quality)"
        )
        self.assertEqual(MJ.extract_prompt(text), "copper torus --ar 1:1")

    def test_unique_contains_rejects_ambiguity(self):
        messages = [
            {"id": "a", "text": "torus one", "buttons": ["U1"]},
            {"id": "b", "text": "torus two", "buttons": ["U1"]},
        ]
        with self.assertRaises(MJ.MjDiscordError):
            MJ.select_unique_message(messages, contains="torus", require_button="U1")

    def test_modal_actions_not_supported(self):
        self.assertNotIn("Vary (Region)", MJ.SUPPORTED_ACTIONS)
        self.assertNotIn("Custom Zoom", MJ.SUPPORTED_ACTIONS)

    def test_remix_capable_actions(self):
        self.assertIn("V1", MJ.REMIX_CAPABLE_ACTIONS)
        self.assertIn("Vary (Subtle)", MJ.REMIX_CAPABLE_ACTIONS)
        self.assertNotIn("U1", MJ.REMIX_CAPABLE_ACTIONS)

    def test_action_parser_accepts_remix_flags(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "action", "--message-id", "m", "--button", "V1", "--accept-remix",
        ])
        self.assertTrue(args.accept_remix)
        self.assertIsNone(args.remix_prompt)

    def test_remix_parser_inspect(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "remix", "--dialog-contains", "brass", "inspect",
        ])
        self.assertEqual(args.remix_action, "inspect")
        self.assertEqual(args.dialog_contains, "brass")

    def test_remix_parser_submit_prompt(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "remix", "submit", "--prompt", "replacement prompt", "--no-wait",
        ])
        self.assertEqual(args.remix_action, "submit")
        self.assertEqual(args.prompt, "replacement prompt")
        self.assertTrue(args.no_wait)

    def test_upload_parser_accepts_multiple_files(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "upload", "a.png", "b.webp",
        ])
        self.assertEqual(args.files, ["a.png", "b.webp"])

    def test_imagine_parser_accepts_multiple_images(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "imagine", "prompt", "--image", "a.png", "--image", "b.png",
        ])
        self.assertEqual(args.image, ["a.png", "b.png"])

    def test_remix_parser_cancel(self):
        parser = MJ.build_parser()
        args = parser.parse_args([
            "--channel-url", "https://discord.com/channels/1/2",
            "remix", "cancel",
        ])
        self.assertEqual(args.remix_action, "cancel")

    def test_read_only_completion_markers(self):
        self.assertIn("Your info -", MJ.READ_ONLY_COMPLETION_MARKERS["info"])
        self.assertIn("GETTING STARTED?", MJ.READ_ONLY_COMPLETION_MARKERS["help"])
        self.assertIn("Adjust your settings here.", MJ.READ_ONLY_COMPLETION_MARKERS["settings"])

    def test_classify_midjourney_message_grid_and_selected(self):
        self.assertEqual(
            MEDIA.classify_midjourney_message({
                "text": "prompt - @elaine",
                "buttons": ["U1", "U2", "U3", "U4"],
                "original_urls": ["https://cdn.discordapp.com/a.webp"],
            }),
            "grid",
        )
        self.assertEqual(
            MEDIA.classify_midjourney_message({
                "text": "prompt - Image #2 @elaine",
                "buttons": ["Vary (Subtle)"],
                "original_urls": ["https://cdn.discordapp.com/a.png"],
            }),
            "selected_image",
        )

    def test_url_filename_decodes_attachment_name(self):
        self.assertEqual(
            MEDIA._url_filename(
                "https://cdn.discordapp.com/attachments/1/2/ref%20image.png?x=1"
            ),
            "ref image.png",
        )

    def test_default_filename(self):
        url = "https://cdn.discordapp.com/attachments/1/2/output.webp?x=1"
        self.assertEqual(MJ.default_filename(url), "output.webp")


if __name__ == "__main__":
    unittest.main()
