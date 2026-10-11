"""Pointer races and input post-conditions against a fake CDP peer."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from browser_runtime.actions import pointer_click, type_text
from browser_cdp_core import BrowserCdpError
from browser_runtime.dom import SelectorGuard


class ActionTests(unittest.TestCase):
    class Peer:
        def __init__(self):
            self.calls=[]
        def call(self,method,params):
            self.calls.append((method,params))
            return {}
        def evaluate(self,*args,**kwargs):
            return {'href':'https://example.org','target_present':True}

    def test_replaced_on_press_cancels_release_outside_page(self):
        peer=self.Peer()
        with patch('browser_runtime.actions.prepare_point',return_value={'x':10,'y':20}), patch('browser_runtime.actions.assert_same',side_effect=[None,BrowserCdpError('changed',code='ELEMENT_CHANGED_DURING_ACTION')]):
            with self.assertRaises(BrowserCdpError) as caught:
                pointer_click(peer,'#button')
        self.assertEqual(caught.exception.code,'ELEMENT_CHANGED_DURING_ACTION')
        self.assertEqual(peer.calls[-1][1]['type'],'mouseReleased')
        self.assertEqual(peer.calls[-1][1]['x'],-1)

    def test_occlusion_before_press_never_presses(self):
        peer=self.Peer()
        with patch('browser_runtime.actions.prepare_point',return_value={'x':10,'y':20}),patch('browser_runtime.actions.assert_same',side_effect=BrowserCdpError('blocked',code='ELEMENT_OCCLUDED')):
            with self.assertRaises(BrowserCdpError):
                pointer_click(peer,'#button')
        self.assertEqual([p['type'] for _,p in peer.calls],['mouseMoved'])

    def test_input_verifies_visible_value_and_invalid_state(self):
        peer=self.Peer()
        state={'value':'wrong','focused':True,'identity':1,'aria_invalid':'true'}
        peer.evaluate=lambda *a,**k:state
        with patch('browser_runtime.actions.pointer_click',return_value={'interaction':{}}):
            with self.assertRaises(BrowserCdpError) as caught:
                type_text(peer,'#editor','expected',SelectorGuard())
        self.assertEqual(caught.exception.code,'INPUT_VERIFICATION_FAILED')

    def test_focus_failure_sends_no_keys(self):
        peer=self.Peer()
        peer.evaluate=lambda *a,**k:{'focused':False}
        with patch('browser_runtime.actions.pointer_click',return_value={'interaction':{}}):
            with self.assertRaises(BrowserCdpError) as caught:
                type_text(peer,'#editor','expected')
        self.assertEqual(caught.exception.code,'FOCUS_FAILED')
        self.assertEqual(peer.calls,[])
