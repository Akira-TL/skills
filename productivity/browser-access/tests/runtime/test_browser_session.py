"""Connection reuse and closed/changed target isolation, using a fake CDP peer."""
import io
import json
import sys
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from browser_cdp_core import BrowserCdpError, CdpClient
from browser_session import BrowserSession, TargetLock, serve_session

TARGET = {'id':'one','url':'https://example.org/channel/1','title':'channel',
          'type':'page','webSocketDebuggerUrl':'ws://unused'}


class FakePage:
    def __init__(self):
        self._events = []
        self.url = TARGET['url']
        self.loader = 'doc1'
        self.connections = 0
    def __enter__(self):
        self.connections += 1
        return self
    def __exit__(self, *args):
        pass
    def call(self, method, params=None):
        if method == 'Page.getFrameTree':
            return {'frameTree':{'frame':{'id':'main','loaderId':self.loader,'url':self.url}}}
        return {}
    def evaluate(self, expression, **options):
        if expression == '({url:location.href,title:document.title})':
            return {'url':self.url,'title':'channel'}
        return 42


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.peer = FakePage()
        self.targets = [TARGET.copy(), {**TARGET,'id':'two','url':'https://example.org/channel/2'}]
        self.patches = [patch('browser_runtime.session.list_targets', side_effect=lambda *a, **k:self.targets),
                        patch('browser_runtime.session.page_client', return_value=self.peer)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_hundred_reads_open_only_one_page_connection(self):
        with BrowserSession('http://unused', target='one') as page:
            for _ in range(100):
                self.assertEqual(page.execute('eval', expression='42')['value'],42)
        self.assertEqual(self.peer.connections,1)

    def test_manual_navigation_fails_and_cannot_be_rebound(self):
        with BrowserSession('http://unused', target='one') as page:
            self.peer.url = self.targets[0]['url'] = self.targets[1]['url']
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('inspect')
            self.assertEqual(caught.exception.code,'TARGET_LOCK_VIOLATION')
            self.peer.url = self.targets[0]['url'] = TARGET['url']
            with self.assertRaises(BrowserCdpError):
                page.execute('inspect')

    def test_closed_tab_never_selects_other_tab(self):
        with BrowserSession('http://unused', target='one') as page:
            self.targets.pop(0)
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('inspect')
            self.assertEqual(caught.exception.code,'TARGET_LOCK_VIOLATION')

    def test_same_url_reload_is_navigation(self):
        with BrowserSession('http://unused', target='one') as page:
            self.peer.loader = 'doc2'
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('title')
            self.assertEqual(caught.exception.code,'NAVIGATION_DETECTED')

    def test_jsonl_errors_keep_ids_and_stream_alive(self):
        with BrowserSession('http://unused', target='one') as page:
            sink = io.StringIO()
            serve_session(page,io.StringIO('{"id":1,"op":"unknown"}\ninvalid\n{"id":2,"op":"title"}\n'),sink)
            rows = [json.loads(line) for line in sink.getvalue().splitlines()]
            self.assertEqual(rows[0]['id'],1)
            self.assertEqual(rows[0]['error_code'],'INVALID_ARGUMENT')
            self.assertFalse(rows[1]['ok'])
            self.assertTrue(rows[2]['ok'])

    def test_origin_and_title_constraints(self):
        for lock in [TargetLock('one',TARGET['url'],'https://other.org'),
                     TargetLock('one',TARGET['url'],expected_title_regex='^different$')]:
            with self.assertRaises(BrowserCdpError):
                lock.validate(TARGET)

    def test_interleaved_events_do_not_replace_response(self):
        class Socket:
            def send(self, payload):
                self.payload = json.loads(payload)
            def recv(self):
                return next(self.messages)
        socket = Socket()
        socket.messages = iter([json.dumps({'method':'Page.navigatedWithinDocument','params':{}}),
                                json.dumps({'id':1,'result':{'answer':42}})])
        client = CdpClient('ws://unused')
        client._ws = socket
        self.assertEqual(client.call('test'),{'answer':42})
        self.assertEqual(len(client._events),1)

    def test_public_module_import_does_not_write_payload_bytecode(self):
        source=Path(__file__).resolve().parents[2]/'scripts'
        with tempfile.TemporaryDirectory() as folder:
            payload=Path(folder)/'payload'
            shutil.copytree(source,payload,ignore=shutil.ignore_patterns('__pycache__'))
            code=f"import sys;sys.path.insert(0,{str(payload)!r});import browser_session"
            subprocess.run(['uv','run','--no-project','python','-B','-c',code],check=True,capture_output=True,text=True)
            self.assertEqual(list(payload.rglob('*.pyc')),[])
