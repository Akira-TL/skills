from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mj_discord.py"
SPEC = importlib.util.spec_from_file_location("mj_discord", MODULE_PATH)
assert SPEC and SPEC.loader
MJ = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MJ)


class MjDiscordPureTests(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(
            MJ.normalize_url("https://discord.com/channels/1/2/?x=1"),
            "https://discord.com/channels/1/2",
        )

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

    def test_default_filename(self):
        url = "https://cdn.discordapp.com/attachments/1/2/output.webp?x=1"
        self.assertEqual(MJ.default_filename(url), "output.webp")


if __name__ == "__main__":
    unittest.main()
