"""多页待办必须由进程保留；Agent 只确认裁决，不决定采样范围。"""
import sys
import unittest
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from watch_controls import Controls, Observation
from monitor_session import ReviewQueue, serve


def page(target, *, identity='u1', running=False, conversation='chat', sampled=True):
    return Observation(target, 'https://chatgpt.com/c/' + conversation,
                       Controls(int(running), int(not running), 1, False, 0, 0, 1, identity),
                       sampled=sampled)


class QueueTests(unittest.TestCase):
    def ack(self, queue, token, disposition, user='u1'):
        queue.acknowledge(token, disposition, reviewed_version='a'*64, latest_user_id=user)

    def protocol(self, commands, sample, **options):
        reader, writer = os.pipe()
        self.addCleanup(os.close, reader)
        os.write(writer, commands.encode())
        os.close(writer)
        output = io.StringIO()
        serve(sample, reader, output, **options)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_protocol_never_discards_second_page_and_stops_only_on_explicit_stop(self):
        replies = self.protocol(
            '{"op":"status","id":1}\n' + json.dumps({'op':'ack','token':'1','disposition':'complete',
              'reviewed_version':'a'*64,'latest_user_id':'u1'}) + '\n'
            '{"op":"status","id":2}\n{"op":"stop"}\n',
            lambda: (page('one', conversation='a'), page('two', conversation='b')))
        self.assertEqual(replies[-1]['kind'], 'monitor-stopped')
        self.assertEqual(len(replies[1]['pending']), 2)
        self.assertEqual([x['conversation'] for x in replies[-2]['pending']], ['b'])
        self.assertEqual(len(replies[-2]['observations']), 2)

    def test_process_samples_past_thirty_minutes_without_exiting(self):
        clock, samples = [0.0], []
        def sample():
            samples.append(clock[0])
            return (page('one', running=True),)
        def wait(readers, *_):
            if clock[0] >= 1860:
                return readers, [], []
            clock[0] += 60
            return [], [], []
        with patch('monitor_session.select.select', side_effect=wait):
            replies = self.protocol('{"op":"stop"}\n', sample, clock=lambda: clock[0])
        self.assertEqual(samples, list(range(0, 1861, 60)))
        self.assertEqual(replies[-1]['kind'], 'monitor-stopped')

    def test_sample_failure_is_reported_and_recovery_does_not_exit(self):
        clock, calls = [0.0], [0]
        def sample():
            calls[0] += 1
            if calls[0] == 1:
                raise TimeoutError('private details')
            return (page('one'),)
        def wait(readers, *_):
            if clock[0] == 0:
                clock[0] += 60
                return [], [], []
            return readers, [], []
        with patch('monitor_session.select.select', side_effect=wait):
            replies = self.protocol('{"op":"status"}\n{"op":"stop"}\n', sample, clock=lambda: clock[0])
        self.assertEqual(replies[0]['sampling_error']['error_type'], 'TimeoutError')
        self.assertIsNone(replies[1]['sampling_error'])
        self.assertEqual(len(replies[1]['pending']), 1)
        self.assertNotIn('private', json.dumps(replies))

    def test_end_of_input_cancels_foreground_monitor(self):
        replies = self.protocol('', lambda: (page('one'),))
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]['kind'], 'monitor-started')

    def test_pending_pages_survive_status_and_other_pages_acknowledgement(self):
        queue = ReviewQueue()
        queue.update((page('one', conversation='a'), page('two', conversation='b')))
        first = queue.status()
        self.assertEqual(len(first['pending']), 2)
        self.assertEqual(queue.status(), first)
        one = next(x for x in first['pending'] if x['conversation'] == 'a')
        self.ack(queue, one['token'], 'complete')
        queue.update((page('one', conversation='a'), page('two', conversation='b')))
        self.assertEqual([p['conversation'] for p in queue.status()['pending']], ['b'])
        self.assertEqual(len(queue.status()['observations']), 2)

    def test_new_user_identity_clears_human_pause_even_with_same_count(self):
        queue = ReviewQueue()
        queue.update((page('one'),))
        self.ack(queue, queue.status()['pending'][0]['token'], 'human')
        self.assertEqual(queue.status()['pending'], [])
        queue.update((page('one', identity='u2'),))
        self.assertEqual(len(queue.status()['pending']), 1)
        self.assertEqual(queue.status()['decisions'], [])

    def test_navigation_does_not_inherit_old_pause(self):
        queue = ReviewQueue()
        queue.update((page('one', conversation='old'),))
        self.ack(queue, queue.status()['pending'][0]['token'], 'human')
        queue.update((page('one', conversation='new'),))
        self.assertEqual(queue.status()['decisions'], [])
        self.assertEqual(queue.status()['pending'][0]['conversation'], 'new')

    def test_stale_ack_and_unknown_decision_cannot_remove_pending(self):
        queue = ReviewQueue()
        queue.update((page('one'),))
        old = queue.status()['pending'][0]['token']
        queue.update((page('one', identity='u2'),))
        with self.assertRaises(ValueError):
            self.ack(queue, old, 'complete')
        current = queue.status()['pending'][0]['token']
        with self.assertRaises(ValueError):
            self.ack(queue, current, 'local-code-not-authorized')
        self.assertEqual(len(queue.status()['pending']), 1)

    def test_generation_resumption_invalidates_old_pending_and_completion(self):
        queue = ReviewQueue()
        queue.update((page('one'),))
        old = queue.status()['pending'][0]['token']
        self.ack(queue, old, 'complete')
        queue.update((page('one', running=True),))
        self.assertEqual(queue.status()['decisions'], [])
        queue.update((page('one'),))
        self.assertEqual(len(queue.status()['pending']), 1)

    def test_duplicate_tabs_are_one_pending_with_all_drafts_preserved(self):
        queue = ReviewQueue()
        queue.update((page('one'), page('two')))
        self.assertEqual(len(queue.status()['pending']), 1)
        self.assertEqual(queue.status()['pending'][0]['targets'], ['one', 'two'])
        self.assertEqual(len(queue.status()['observations']), 2)

    def test_closing_one_tab_never_removes_another_conversations_pending_review(self):
        queue = ReviewQueue()
        queue.update((page('one', conversation='a'), page('two', conversation='b')))
        queue.update((page('two', conversation='b'),))
        self.assertEqual([p['conversation'] for p in queue.status()['pending']], ['b'])
        self.assertEqual([p['target'] for p in queue.status()['observations']], ['two'])

    def test_failed_sampling_retains_pending_but_prevents_acknowledgement(self):
        queue = ReviewQueue()
        queue.update((page('one'),))
        token = queue.status()['pending'][0]['token']
        queue.update((page('one', sampled=False),))
        self.assertEqual(len(queue.status()['pending']), 1)
        with self.assertRaises(ValueError):
            self.ack(queue, token, 'complete')
        queue.update(())
        self.assertEqual(queue.status()['pending'], [])

    def test_old_user_instruction_cannot_ack_current_review_as_human_pause(self):
        queue = ReviewQueue()
        queue.update((page('one', identity='new-r3-request'),))
        token = queue.status()['pending'][0]['token']
        with self.assertRaises(ValueError):
            self.ack(queue, token, 'human', user='old-r2-request')
        self.assertEqual(len(queue.status()['pending']), 1)


if __name__ == '__main__':
    unittest.main()
