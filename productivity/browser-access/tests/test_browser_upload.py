import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from browser_runtime.upload import UploadFile, prepare_file, validate_files, upload_files
from browser_cdp_core import BrowserCdpError

class UploadTests(unittest.TestCase):
    def test_missing_file_has_stable_code(self):
        with self.assertRaises(BrowserCdpError) as caught:
            prepare_file('/definitely/absent.png','Linux')
        self.assertEqual(caught.exception.code,'FILE_NOT_FOUND')
    def test_accept_count_and_size_constraints(self):
        file=UploadFile('/tmp/a.png','/tmp/a.png','a.png',20,'image/png')
        state={'enabled':True,'multiple':False,'accept':'image/*'}
        validate_files([file],state)
        for files,changes,limits in [([file,file],{},{}),([file],{'accept':'.jpeg'},{}),([file],{'enabled':False},{}),([file],{}, {'max_file_bytes':10}),([file],{}, {'max_total_bytes':10})]:
            with self.assertRaises(BrowserCdpError) as caught:
                validate_files(files,{**state,**changes},**limits)
            self.assertEqual(caught.exception.code,'FILE_CONSTRAINT_VIOLATION')
    def test_linux_browser_in_wsl_keeps_linux_path(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as f,patch('browser_runtime.upload.running_in_wsl',return_value=True):
            self.assertEqual(prepare_file(f.name,'Linux').browser_path,f.name)
    def test_browser_file_list_is_verified_even_without_protocol_error(self):
        class Peer:
            def evaluate(self,expression):
                return 'Linux' if expression=='navigator.platform' else {'enabled':True,'multiple':False,'accept':'','files':[]}
            def call(self,method,params):
                if method=='Runtime.evaluate':return {'result':{'objectId':'input'}}
                if method=='Runtime.callFunctionOn':return {'result':{'value':{'connected':True,'enabled':True,'multiple':False,'accept':'','files':[]}}}
                return {}
        with tempfile.NamedTemporaryFile() as f:
            with self.assertRaises(BrowserCdpError) as caught:
                upload_files(Peer(),'#file',[f.name])
        self.assertEqual(caught.exception.code,'UPLOAD_VERIFICATION_FAILED')
