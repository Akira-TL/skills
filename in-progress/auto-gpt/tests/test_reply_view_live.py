"""独立本地页面验证回复读取，不接触已登录浏览器或真实任务。"""
import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / 'productivity/browser-access/scripts'))
if os.environ.get('BROWSER_LIVE_TESTS') == '1':
    from browser_cdp_core import http_json, page_client, wait_ready
    from browser_session import BrowserSession

VIEW = (Path(__file__).parents[1] / 'scripts/reply-view.js').read_text()
ENDPOINT = os.environ.get('BROWSER_FIXTURE_ENDPOINT', 'http://127.0.0.1:19322')
URL = 'http://127.0.0.1:19323/dynamic.html'
HTML = '''<main><button id="model">5.6 极高</button><p class="user">核对论文全文</p>
<article id="reply"><p>已核对第一部分；第二部分尚未完成。</p><button class="ui">正在打开 ForgeRelay</button>
<pre class="payload">SGVsbG8=</pre><p>还需检查重建结果。</p><p hidden>隐藏草稿</p></article>
<div role="textbox" contenteditable="true" style="width:300px;height:40px"></div>
<button aria-label="发送">发送</button></main>'''
OPTIONS = {'reply_selector':'#reply', 'user_selector':'.user', 'model_selector':'#model',
           'ui_selector':'.ui', 'payload_selector':'.payload', 'payload_text':False}


@unittest.skipUnless(os.environ.get('BROWSER_LIVE_TESTS') == '1', '需 browser_fixture.sh 启动独立实例')
class ReplyViewLiveTests(unittest.TestCase):
    def setUp(self):
        self.target = http_json(ENDPOINT, '/json/new?' + URL, method='PUT')
        self.addCleanup(lambda: urllib.request.urlopen(ENDPOINT + '/json/close/' + self.target['id']).close())
        with page_client(self.target, timeout=5) as client:
            wait_ready(client, timeout=5)
        self.page = BrowserSession(ENDPOINT, target=self.target['id'], expected_url=URL, timeout=5)
        self.page.__enter__()
        self.addCleanup(self.page.__exit__, None, None, None)
        self.page.evaluate('document.body.innerHTML=' + json.dumps(HTML))

    def read(self, **options):
        expression = f'(async () => {{ {VIEW}; return await replyView({json.dumps(OPTIONS | options)}); }})()'
        return self.page.evaluate(expression, await_promise=True)

    def test_full_reply_and_payload_metadata_without_tool_blob(self):
        result = self.read()
        self.assertIn('已核对第一部分；第二部分尚未完成。', result['text'])
        self.assertIn('还需检查重建结果。', result['text'])
        self.assertNotIn('ForgeRelay', result['text'])
        self.assertNotIn('SGVsbG8=', result['text'])
        self.assertNotIn('隐藏草稿', result['text'])
        self.assertNotIn('text', result['payloads'][0])
        self.assertEqual(result['payloads'][0]['length'], 8)
        self.assertEqual(result['user_count'], 1)
        self.assertEqual(result['latest_user'], '核对论文全文')

    def test_ui_change_does_not_change_reviewed_reply_version(self):
        before = self.read()
        self.page.evaluate("document.querySelector('.ui').textContent='已打开 ForgeRelay'")
        after = self.read()
        self.assertEqual(before['version'], after['version'])
        self.page.evaluate("document.querySelector('#reply p').textContent='任务已完成，需要人工确认'")
        self.assertNotEqual(before['version'], self.read()['version'])

    def test_payload_change_changes_version_and_full_read_keeps_version(self):
        before = self.read()
        full = self.read(payload_text=True)
        self.assertEqual(full['payloads'][0]['text'], 'SGVsbG8=')
        self.assertEqual(before['version'], full['version'])
        self.page.evaluate("document.querySelector('.payload').textContent='Changed result'")
        self.assertNotEqual(before['version'], self.read()['version'])

    def test_unknown_or_overlapping_structure_fails_closed(self):
        from browser_cdp_core import BrowserCdpError
        for options in ({'reply_selector':'.missing'}, {'reply_selector':'p'},
                        {'ui_selector':'.payload'}):
            with self.subTest(options=options), self.assertRaises(BrowserCdpError):
                self.read(**options)


if __name__ == '__main__':
    unittest.main()
