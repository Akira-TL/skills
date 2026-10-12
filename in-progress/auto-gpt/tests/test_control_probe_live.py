"""在独立本地 Chromium 页面验证提示选择器，不连接真实 ChatGPT。"""
import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "productivity/browser-access/scripts"))
if os.environ.get("BROWSER_LIVE_TESTS") == "1":
    from browser_cdp_core import http_json, page_client, wait_ready
    from browser_session import BrowserSession

PROBE = (Path(__file__).parents[1] / "scripts/observe-controls.js").read_text(encoding="utf-8")
ENDPOINT = os.environ.get("BROWSER_FIXTURE_ENDPOINT", "http://127.0.0.1:19322")
URL = "http://127.0.0.1:19323/dynamic.html"
NOTICE = "连接已中断，正在等待完整答复"


@unittest.skipUnless(os.environ.get("BROWSER_LIVE_TESTS") == "1", "需通过 browser_fixture.sh 启动独立测试实例")
class ControlProbeLiveTests(unittest.TestCase):
    def setUp(self):
        self.target = http_json(ENDPOINT, "/json/new?" + URL, method="PUT")
        with page_client(self.target, timeout=5) as client:
            wait_ready(client, timeout=5)
        self.addCleanup(self.close_target)

    def close_target(self):
        urllib.request.urlopen(ENDPOINT + "/json/close/" + self.target["id"]).close()

    def probe(self, html):
        with BrowserSession(ENDPOINT, target=self.target["id"], expected_url=URL, timeout=5) as page:
            page.evaluate("document.body.innerHTML=" + json.dumps(html))
            return page.evaluate(PROBE)

    def test_status_notice_detected_despite_stop_button_and_no_alert(self):
        result = self.probe(f'<main><div role="status"><span class="text-chatgpt-recovery">{NOTICE}</span></div>'
                            '<button aria-label="停止">停止</button><div role="textbox" contenteditable="true"></div></main>')
        self.assertTrue(result["connection_lost"])
        self.assertEqual(result["stop"], 1)
        self.assertEqual(result["alerts"], 0)

    def test_same_words_in_reply_are_not_a_connection_notice(self):
        result = self.probe(f'<main><article><p>{NOTICE}</p></article></main>')
        self.assertFalse(result["connection_lost"])

    def test_hidden_notice_is_not_reported(self):
        result = self.probe(f'<main><div role="status" style="display:none">'
                            f'<span class="text-chatgpt-recovery">{NOTICE}</span></div></main>')
        self.assertFalse(result["connection_lost"])


if __name__ == "__main__":
    unittest.main()
