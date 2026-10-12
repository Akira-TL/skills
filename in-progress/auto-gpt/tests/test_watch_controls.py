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


def page(target="one", *, running=False, draft=False, turns=1, alerts=0, dialogs=0, lost=False):
    return Observation(target, "https://chatgpt.com/c/test-conversation",
                       Controls(int(running), int(not running), 1, draft, alerts, dialogs, turns, "", lost))


class WatchTests(unittest.TestCase):
    def test_thirty_minute_timeout_preserves_baseline_without_extra_sample(self):
        time = [0.0]
        samples = []
        def sample():
            samples.append(time[0])
            return (page(running=True),)
        def sleep(seconds):
            time[0] += seconds
        event = watch(sample, baseline=None, clock=lambda: time[0], sleep=sleep)
        self.assertEqual(time[0], 1800)
        self.assertEqual(samples, list(range(0, 1800, 60)))
        self.assertEqual(event.reason, "watch-timeout")
        self.assertEqual(event.targets, ())
        self.assertEqual(event.observations, (page(running=True),))

    def test_timeout_rearming_preserves_connection_grace_period(self):
        time = [0.0]
        def sleep(seconds):
            time[0] += seconds
        sample = lambda: (page(running=True, lost=True),)
        first = watch(sample, baseline=None, clock=lambda: time[0], sleep=sleep,
                      max_wait_seconds=150)
        self.assertEqual(first.reason, "watch-timeout")
        self.assertEqual(time[0], 150)
        baseline = module.read_baseline(json.dumps([module.asdict(p) for p in first.observations]))
        second = watch(sample, baseline=baseline, clock=lambda: time[0], sleep=sleep)
        self.assertEqual(second.reason, "connection-interrupted")
        self.assertEqual(second.observations[0].connection.since, 0)
        self.assertEqual(time[0], 210)

    def test_invalid_timeout_is_rejected_before_sampling(self):
        for seconds in (0, -1, float("inf"), float("nan")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                watch(lambda: self.fail("invalid timeout sampled"), baseline=None,
                      max_wait_seconds=seconds)

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

    def test_interrupted_notice_waits_three_minutes_while_stop_button_remains(self):
        time = [0.0]
        waits = []
        def sleep(seconds):
            waits.append(seconds)
            time[0] += seconds
        event = watch(lambda: (page(running=True, lost=True),), baseline=None,
                      clock=lambda: time[0], sleep=sleep)
        self.assertEqual(waits, [60, 60, 60])
        self.assertEqual(event.reason, "connection-interrupted")
        self.assertEqual(event.targets, ("one",))
        self.assertEqual(event.observations[0].controls.stop, 1)
        self.assertEqual(event.observations[0].connection.last_seen - event.observations[0].connection.since, 180)
        self.assertTrue(event.observations[0].connection.reported)

    def test_natural_return_to_composer_cancels_refresh_candidate(self):
        time = [0.0]
        frames = iter([(page(running=True, lost=True),), (page(running=True, lost=True),), (page(),)])
        def sleep(seconds):
            time[0] += seconds
        event = watch(lambda: next(frames), baseline=None, clock=lambda: time[0], sleep=sleep)
        self.assertEqual(event.reason, "controls-changed")
        self.assertEqual(time[0], 120)
        self.assertIsNone(event.observations[0].connection)

    def test_stale_interruption_text_with_composer_does_not_start_timer(self):
        observations = module.observe_connections(None, (page(lost=True),), 100)
        self.assertIsNone(observations[0].connection)

    def test_notice_disappearing_then_returning_starts_a_new_grace_period(self):
        initial = module.observe_connections(None, (page(running=True, lost=True),), 0)
        gone = module.observe_connections(initial, (page(running=True),), 60)
        returned = module.observe_connections(gone, (page(running=True, lost=True),), 120)
        self.assertIsNone(gone[0].connection)
        self.assertEqual(returned[0].connection.since, 120)

    def test_sampling_gap_does_not_count_unobserved_time_as_persistent_loss(self):
        initial = module.observe_connections(None, (page(running=True, lost=True),), 0)
        after_gap = module.observe_connections(initial, (page(running=True, lost=True),), 300)
        self.assertEqual(after_gap[0].connection.since, 300)

    def test_reported_loss_survives_rearming_without_repeated_notification(self):
        baseline = (module.Observation("one", "https://chatgpt.com/c/test-conversation",
                    page(running=True, lost=True).controls, module.ConnectionNotice(0, 180, True)),)
        restored = module.read_baseline(json.dumps([module.asdict(p) for p in baseline]))
        current = module.observe_connections(restored, (page(running=True, lost=True),), 240)
        self.assertTrue(current[0].connection.reported)
        self.assertEqual(current[0].connection.since, 0)
        def cancel(_seconds):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            watch(lambda: (page(running=True, lost=True),), baseline=current,
                  clock=lambda: 240, sleep=cancel)

    def test_invalid_connection_timing_is_rejected(self):
        value = module.asdict(page(running=True, lost=True))
        value["connection"] = {"since": 10, "last_seen": 2, "reported": False}
        with self.assertRaises(ValueError):
            module.read_baseline(json.dumps([value]))

    def test_stale_timing_in_recovered_baseline_does_not_apply_to_new_loss(self):
        baseline = (module.Observation("one", "https://chatgpt.com/c/test-conversation",
                    page().controls, module.ConnectionNotice(0, 180, True)),)
        current = module.observe_connections(baseline, (page(running=True, lost=True),), 240)
        self.assertEqual(current[0].connection.since, 240)
        self.assertFalse(current[0].connection.reported)

    def test_observed_new_turn_restarts_the_grace_period(self):
        baseline = module.observe_connections(None, (page(running=True, lost=True, turns=1),), 0)
        current = module.observe_connections(baseline, (page(running=True, lost=True, turns=2),), 60)
        self.assertEqual(current[0].connection.since, 60)


if __name__ == "__main__":
    unittest.main()
