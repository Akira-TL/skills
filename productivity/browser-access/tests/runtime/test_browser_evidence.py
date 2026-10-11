import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from browser_runtime.evidence import redact, safe_url, capture_evidence
from browser_cdp_core import BrowserCdpError

class EvidenceTests(unittest.TestCase):
    def test_sensitive_headers_and_signed_url_are_redacted(self):
        value=redact({'headers':{'Cookie':'secret'},'Authorization':'Bearer abc','url':'https://user:pass@example.org/a?token=secret#frag','message':'token=secret Bearer abc'})
        self.assertNotIn('secret',str(value))
        self.assertNotIn('user:pass',str(value))
        self.assertNotIn('headers',value)
        self.assertEqual(value['url'],'https://example.org/a')
    def test_bounded_nested_evidence(self):
        self.assertEqual(len(redact(['x']*200)),100)
        self.assertEqual(len(redact('x'*20000)),12000)

    def test_unwritable_evidence_preserves_original_error(self):
        error=BrowserCdpError('missing',code='ELEMENT_NOT_FOUND')
        with patch('browser_runtime.evidence.tempfile.mkdtemp',side_effect=OSError('read only')):
            self.assertIsNone(capture_evidence(object(),'click',{},error,0.1))
        self.assertEqual(error.code,'ELEMENT_NOT_FOUND')
        self.assertIn('evidence_capture_error',error.context)
