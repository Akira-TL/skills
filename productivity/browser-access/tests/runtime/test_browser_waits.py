import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from browser_runtime.waits import wait_condition
from browser_cdp_core import BrowserCdpError

class WaitTests(unittest.TestCase):
    class Peer:
        timeout=1
        def __init__(self):self.expressions=[]
        def evaluate(self,expression,**kwargs):
            self.expressions.append(expression)
            if '?.count||0' in expression:return 7
            if expression=='false':return False
            if 'return [...root.querySelectorAll' in expression:return []
            return True
    def test_timeout_contains_observation_and_mutation_count(self):
        peer=self.Peer()
        with self.assertRaises(BrowserCdpError) as caught:
            wait_condition(peer,'condition',{'expression':'false','timeout':0.01,'poll':0.01})
        self.assertEqual(caught.exception.code,'WAIT_TIMEOUT')
        self.assertEqual(caught.exception.context['last_observed'],False)
        self.assertEqual(caught.exception.context['mutation_count'],7)
        self.assertIn('observer.disconnect',peer.expressions[-1])
    def test_new_element_uses_baseline_identity(self):
        peer=self.Peer()
        original=peer.evaluate
        peer.evaluate=lambda expression,**kwargs: [{'identity':2,'text':'new'}] if 'return [...root.querySelectorAll' in expression else original(expression,**kwargs)
        result=wait_condition(peer,'new',{'selector':'.message','baseline':[1]})
        self.assertEqual(result['value'][0]['identity'],2)
    def test_initial_state_mismatch_is_explicit(self):
        peer=self.Peer()
        with self.assertRaises(BrowserCdpError) as caught:
            wait_condition(peer,'transition',{'selector':'#status','initial_text':'sending','until_expression':'true'})
        self.assertEqual(caught.exception.code,'WAIT_INITIAL_STATE_MISMATCH')
