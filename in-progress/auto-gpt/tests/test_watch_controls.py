"""验证只读观察的事件、等待节奏和接管范围；不调用真实 ChatGPT 模型。"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
script = Path(__file__).parents[1] / "scripts" / "watch_controls.py"
spec = importlib.util.spec_from_file_location("auto_gpt_watch", script)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Controls, Observation, watch = module.Controls, module.Observation, module.watch


def page(target="one", *, running=False, draft=False, turns=1, alerts=0, dialogs=0):
    return Observation(target, "https://chatgpt.com/c/test-conversation",
                       Controls(int(running), int(not running), 1, draft, alerts, dialogs, turns, ""))


class WatchTests(unittest.TestCase):
    def test_running_then_composer_waits_a_minute_and_only_returns_end_event(self):
        frames = iter([(page(running=True),), (page(running=True),), (page(),)])
        waits = []
        event = watch(lambda: next(frames), baseline=None, clock=lambda: 0, sleep=waits.append)
        self.assertEqual(waits, [60, 60])
        self.assertEqual(event.reason, "controls-changed")
        self.assertEqual(event.targets, ("one",))
        self.assertEqual(event.observations[0].controls.view, module.View.COMPOSER)

    def test_completed_idle_page_does_not_repeatedly_wake(self):
        frames = iter([(page(),), (page(running=True),), (page(running=True),), (page(turns=2),)])
        waits = []
        event = watch(lambda: next(frames), baseline=(page(),), clock=lambda: 0, sleep=waits.append)
        self.assertEqual(waits, [60, 60, 60])
        self.assertEqual(event.targets, ("one",))

    def test_draft_clear_wakes_agent_without_deciding_or_sending(self):
        event = module.changes((page(draft=True),), (page(),))
        self.assertEqual(event.targets, ("one",))
        self.assertFalse(event.observations[0].controls.draft)
        self.assertEqual(set(json.loads(json.dumps(module.asdict(event)))), {"reason", "targets", "observations"})

    def test_same_conversation_tabs_preserve_each_draft_observation(self):
        current = (page("empty"), page("draft", draft=True))
        event = module.changes(None, current)
        self.assertEqual(event.targets, ("draft", "empty"))
        self.assertTrue(next(p for p in event.observations if p.target == "draft").controls.draft)

    def test_unknown_controls_never_report_composer(self):
        unknown = Observation("one", "https://chatgpt.com/", Controls(0, 0, 1, False, 0, 0, 0, ""))
        event = module.changes((page(running=True),), (unknown,))
        self.assertEqual(event.observations[0].controls.view, module.View.UNKNOWN)
        self.assertIsNone(module.changes((unknown,), (unknown,)))

    def test_dialog_appearing_during_generation_wakes_agent(self):
        event = module.changes((page(running=True),), (page(running=True, dialogs=1),))
        self.assertEqual(event.targets, ("one",))
        self.assertEqual(event.observations[0].controls.view, module.View.RUNNING)

    def test_closed_page_notifies_once(self):
        self.assertEqual(module.changes((page(),), ()).targets, ("one",))
        self.assertIsNone(module.changes((), ()))

    def test_origin_and_conversation_matching(self):
        self.assertEqual(module.conversation("https://chatgpt.com/g/g-example/c/123"), "123")
        self.assertEqual(module.conversation("https://chatgpt.com/"), "")
        for url in ("http://chatgpt.com/c/123", "https://chatgpt.com.example/c/123",
                    "https://example.com/?url=https://chatgpt.com", "https://user@chatgpt.com/c/123"):
            self.assertIsNone(module.conversation(url))

    def test_baseline_round_trip_has_only_control_facts(self):
        original = (page(), page("other", draft=True))
        raw = json.dumps([module.asdict(p) for p in original])
        self.assertEqual(module.read_baseline(raw), original)
        with self.assertRaises(ValueError):
            module.read_baseline('{"unstructured":"state"}')

    def test_invalid_probe_is_rejected_instead_of_assuming_finished(self):
        with self.assertRaises(ValueError):
            module.read_controls({"stop": False})

    def test_cancel_interrupts_wait_instead_of_another_sample(self):
        samples = []
        def sample():
            samples.append(1)
            return (page(running=True),)
        def cancel(_seconds):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            watch(sample, baseline=None, clock=lambda: 0, sleep=cancel)
        self.assertEqual(samples, [1])


if __name__ == "__main__":
    unittest.main()
