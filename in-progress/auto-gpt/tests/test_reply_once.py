"""单次动作测试覆盖未知结果、版本变化和重复标签页，无真实网站发送。"""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True
script = Path(__file__).parents[1] / 'scripts/reply_once.py'
sys.path.insert(0, str(script.parent))
spec = importlib.util.spec_from_file_location('auto_gpt_reply_once', script)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
URL = 'https://chatgpt.com/c/test'
VERSION = 'a' * 64
SELECTORS = module.Selectors('#reply', '.user', '#model')
BEFORE = {'url':URL, 'version':VERSION, 'model':'5.6 极高', 'user_count':1,
          'point':{'x':200, 'y':300}, 'latest_user':'任务'}
AFTER = {**BEFORE, 'user_count':2, 'latest_user':'继续'}
CONTROLS = {'stop':1, 'composer':0, 'editors':1, 'draft':False, 'alerts':0,
            'dialogs':0, 'turns':2, 'latest_turn':''}


class ReplyOnceTests(unittest.TestCase):
    def test_segmented_read_preserves_full_text_and_requires_same_version(self):
        view = {**BEFORE, 'text':'第一段\n需要人工确认\n最后一段', 'length':17,
                'payloads':[], 'focused':True}
        pieces = []
        start = 0
        while True:
            result = module.read_window(view, start=start, limit=6, expected_version=VERSION)
            pieces.append(result['text'])
            self.assertNotIn('point', result)
            self.assertNotIn('focused', result)
            if result['next_start'] is None:
                break
            start = result['next_start']
        self.assertEqual(''.join(pieces), '第一段\n需要人工确认\n最后一段')
        self.assertFalse(result['text_complete'])
        with self.assertRaises(ValueError):
            module.read_window({**view, 'version':'b'*64}, expected_version=VERSION)

    def test_payload_window_returns_no_reply_or_other_payload_body(self):
        view = {**BEFORE, 'text':'正文保持完整', 'payloads':[
            {'index':0, 'text':'abcdefgh', 'length':8, 'sha':'first'},
            {'index':1, 'text':'private other blob', 'length':18, 'sha':'second'}]}
        result = module.read_window(view, payload_index=0, start=2, limit=3, expected_version=VERSION)
        self.assertEqual(result['text'], 'cde')
        self.assertEqual(result['next_start'], 5)
        self.assertEqual(result['sha'], 'first')
        self.assertNotIn('正文', str(result))
        self.assertNotIn('private', str(result))
        with self.assertRaises(ValueError):
            module.read_window(view, start=1)
        with self.assertRaises(ValueError):
            module.read_window(view, payload_index=0)
        for options in ({'start':-1}, {'limit':0}, {'limit':12001}, {'start':999}, {'payload_index':2}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                module.read_window(view, **options)

    def setUp(self):
        self.page = MagicMock()
        self.page.evaluate.return_value = CONTROLS
        self.page.call.return_value = {'targetInfos':[]}
        self.attempt = module.Attempt()

    def run_once(self, **options):
        return module.continue_once(self.page, SELECTORS, url=URL, target='one', version=VERSION,
                                    model='5.6 极高', attempt=self.attempt, **options)

    def test_one_input_and_one_enter_confirmed_in_one_page_session(self):
        with patch.object(module, 'snapshot', side_effect=[BEFORE, BEFORE]), \
             patch.object(module, 'confirmation', return_value={**AFTER, 'controls':CONTROLS}):
            result = self.run_once()
        self.assertTrue(result['attempt']['confirmed'])
        calls = self.page.call.call_args_list
        self.assertEqual(sum(call.args[0] == 'Input.insertText' for call in calls), 1)
        enters = [call for call in calls if call.args[0] == 'Input.dispatchKeyEvent']
        self.assertEqual([call.args[1]['type'] for call in enters], ['keyDown', 'keyUp'])
        for call in calls:
            if call.args[0] in ('Input.insertText', 'Page.bringToFront') or (
                    call.args[0] == 'Input.dispatchKeyEvent' and call.args[1]['type'] == 'keyDown'):
                self.assertIn(VERSION, call.kwargs['guard'])

    def test_reply_or_model_change_stops_before_focus(self):
        for before in ({**BEFORE, 'version':'b'*64}, {**BEFORE, 'model':'Pro'},
                       {**BEFORE, 'user_count':0}):
            with self.subTest(before=before), patch.object(module, 'snapshot', return_value=before), \
                 self.assertRaises(ValueError):
                self.run_once()
            self.page.call.assert_not_called()

    def test_unconfirmed_enter_is_never_retried(self):
        with patch.object(module, 'snapshot', side_effect=[BEFORE, BEFORE]), \
             patch.object(module, 'confirmation', return_value={**BEFORE, 'controls':CONTROLS}):
            result = self.run_once()
        self.assertEqual(result['attempt']['stage'], 'unconfirmed')
        self.assertTrue(result['attempt']['enter_attempted'])
        self.assertFalse(result['attempt']['confirmed'])
        self.assertEqual(result['confirmation']['after_user_count'], 1)
        self.assertEqual(sum(call.args[0] == 'Input.insertText' for call in self.page.call.call_args_list), 1)

    def test_enter_failure_releases_key_but_never_sends_second_enter(self):
        def call(method, params=None, **kwargs):
            if method == 'Target.getTargets':
                return {'targetInfos':[]}
            if method == 'Input.dispatchKeyEvent' and params['type'] == 'keyDown':
                raise TimeoutError('unknown transmission result')
            return {}
        self.page.call.side_effect = call
        with patch.object(module, 'snapshot', side_effect=[BEFORE, BEFORE]), self.assertRaises(TimeoutError):
            self.run_once()
        self.assertTrue(self.attempt.enter_attempted)
        enters = [c.args[1]['type'] for c in self.page.call.call_args_list if c.args[0] == 'Input.dispatchKeyEvent']
        self.assertEqual(enters, ['keyDown', 'keyUp'])

    def test_duplicate_conversation_prevents_text_insertion(self):
        self.page.call.return_value = {'targetInfos':[{'targetId':'two', 'type':'page', 'url':URL}]}
        with patch.object(module, 'snapshot', side_effect=[BEFORE, BEFORE]), self.assertRaises(ValueError):
            self.run_once()
        self.assertFalse(any(c.args[0] == 'Input.insertText' for c in self.page.call.call_args_list))

    def test_model_restriction_is_conservative(self):
        for name in ('', 'Pro', 'GPT 5.6 Pro', 'o3-pro'):
            self.assertFalse(module.non_pro(name))
        self.assertTrue(module.non_pro('5.6 极高'))


if __name__ == '__main__':
    unittest.main()
