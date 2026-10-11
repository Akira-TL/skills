import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from browser_runtime.network import status_matches
from browser_cdp_core import BrowserCdpError
class NetworkPredicateTests(unittest.TestCase):
    def test_status_classes_and_explicit_codes(self):
        self.assertTrue(status_matches(204,'2xx'))
        self.assertFalse(status_matches(403,'2xx'))
        self.assertTrue(status_matches(304,'200,304'))
        self.assertFalse(status_matches(None,'2xx'))
        with self.assertRaises(BrowserCdpError):status_matches(200,'successful')
