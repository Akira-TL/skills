"""Opt-in real Chromium tests; started exclusively by browser_fixture.sh."""
import os
import base64
import tempfile
import sys
import unittest
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from browser_cdp_core import BrowserCdpError, http_json
from browser_session import BrowserSession

ENDPOINT='http://127.0.0.1:19322'
URL='http://127.0.0.1:19323/dynamic.html'

@unittest.skipUnless(os.environ.get('BROWSER_LIVE_TESTS')=='1','set BROWSER_LIVE_TESTS=1 after browser_fixture.sh start')
class LiveTests(unittest.TestCase):
    def setUp(self):
        self.target=http_json(ENDPOINT,'/json/new?'+URL,method='PUT')
        from browser_cdp_core import page_client, wait_ready
        with page_client(self.target,timeout=5) as client:
            wait_ready(client,timeout=5)
        self.addCleanup(lambda:urllib.request.urlopen(ENDPOINT+'/json/close/'+self.target['id']).close())
    def page(self):
        return BrowserSession(ENDPOINT,target=self.target['id'],expected_url=URL,timeout=5)
    def test_scoped_click_ambiguity_overlay_and_scroll(self):
        with self.page() as page:
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('click',selector='.variant')
            self.assertEqual(caught.exception.code,'ELEMENT_AMBIGUOUS')
            result=page.execute('click',selector='.variant',within='#message-two',expect_text='U1',expect_role='button')
            self.assertTrue(result['clicked'])
            self.assertEqual(page.evaluate("document.querySelector('#message-two button').dataset.clicked"),'two')
            self.assertIsNone(page.evaluate("document.querySelector('#message-one button').dataset.clicked"))
            page.evaluate("document.querySelector('#overlay').style.display='block'")
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('click',selector='#editor')
            self.assertEqual(caught.exception.code,'ELEMENT_OCCLUDED')
            page.evaluate("document.querySelector('#overlay').style.display='none'")
            self.assertTrue(page.execute('click',selector='#offscreen')['clicked'])
    def test_replacement_during_press_is_rejected(self):
        with self.page() as page:
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('click',selector='#replace-press')
            self.assertEqual(caught.exception.code,'ELEMENT_CHANGED_DURING_ACTION')
    def test_native_rich_text_and_modal(self):
        with self.page() as page:
            self.assertEqual(page.execute('type',selector='#editor',value='中文输入')['state']['value'],'中文输入')
            self.assertEqual(page.execute('type',selector='#rich',value='可见文本')['state']['value'],'可见文本')
            page.execute('click',selector='#open-modal')
            self.assertEqual(page.execute('type',selector='.field',value='modal',within='#modal')['state']['value'],'modal')
            page.execute('click',selector='.close',within='#modal')
            self.assertTrue(page.evaluate("document.querySelector('#modal').hidden"))

    def test_upload_single_multi_and_rebuilt_hidden_input(self):
        with tempfile.TemporaryDirectory() as folder, self.page() as page:
            data=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
            first=Path(folder)/'中文 图片(1).png'
            second=Path(folder)/'图片(2).png'
            first.write_bytes(data);second.write_bytes(data)
            result=page.execute('upload',selector='.file',within='#upload-one',files=[str(first)])
            self.assertTrue(result['input_rebuilt'])
            self.assertEqual(result['state']['names'],[first.name])
            result=page.execute('upload',selector='.file',within='#upload-one',files=[str(second)])
            self.assertEqual(result['state']['names'],[second.name])
            self.assertEqual(page.evaluate("document.querySelector('#preview').textContent"),second.name)
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('upload',selector='.file',within='#upload-one',files=[str(first),str(second)])
            self.assertEqual(caught.exception.code,'FILE_CONSTRAINT_VIOLATION')
            result=page.execute('upload',selector='.file',within='#upload-two',files=[str(first),str(second)])
            self.assertEqual(result['state']['count'],2)

    def test_wait_transitions_new_elements_stability_and_timeout(self):
        with self.page() as page:
            baseline=page.execute('elements',selector='#messages > div')['value']
            transition=page.execute('wait-transition',selector='#status',initial_text='初始',until_expression="value==='完成'",click='#progress',timeout=2,poll=0.02)
            self.assertIn('完成',transition['transitions'])
            result=page.execute('wait-new',selector='#messages > div',baseline=[item['identity'] for item in baseline],timeout=1)
            self.assertEqual(result['value'][0]['id'],'new-message')
            self.assertTrue(page.execute('wait',dom_stable='#status',stable_ms=80,timeout=1)['met'])
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('wait-mutation',within='#status',until_expression='false',timeout=0.1)
            self.assertEqual(caught.exception.code,'WAIT_TIMEOUT')
            self.assertIn('last_observed',caught.exception.context)
            self.assertIn('mutation_count',caught.exception.context)

    def test_error_evidence_screenshot_and_bounded_snapshot(self):
        with tempfile.TemporaryDirectory() as folder,self.page() as page:
            output=Path(folder)/'element.png'
            self.assertGreater(page.execute('screenshot',selector='#editor',output=str(output))['bytes'],0)
            self.assertTrue(output.read_bytes().startswith(b'\x89PNG'))
            snapshot=page.execute('snapshot',selector='body',max_chars=50)
            self.assertLessEqual(len(snapshot['outerHTML']),50)
            page.evaluate("document.body.insertAdjacentHTML('beforeend','<input name=token value=TOP_SECRET>')")
            with self.assertRaises(BrowserCdpError) as caught:
                page.execute('click',selector='#missing',evidence_on_error=True)
            directory=Path(caught.exception.context['evidence_dir'])
            for name in ('meta.json','screenshot.png','visible-text.txt','controls.json','target.json','console-errors.json'):
                self.assertTrue((directory/name).exists(),name)
            for file in directory.glob('*.json'):
                self.assertNotIn('TOP_SECRET',file.read_text())
            self.assertNotIn('TOP_SECRET',(directory/'visible-text.txt').read_text())

    def test_network_predicates_and_artifacts(self):
        with self.page() as page:
            result=page.execute('network',mode='wait-response',url_regex='/asset\\.png$',status='2xx',click='#request',timeout=2)
            self.assertEqual(result['records'][0]['status'],200)
            self.assertNotIn('headers',result['records'][0])
            self.assertTrue(page.execute('network',mode='wait-idle',url_regex='/asset',idle_ms=50,timeout=1)['met'])
            artifact=page.execute('resolve-artifact',selector='#artifact')
            self.assertEqual(artifact['suggested_filename'],'结果.png')
            fetched=page.execute('browser-fetch',url=artifact['url'],max_bytes=1000)
            self.assertTrue(Path(fetched['output']).read_bytes().startswith(b'\x89PNG'))
            Path(fetched['output']).unlink()
