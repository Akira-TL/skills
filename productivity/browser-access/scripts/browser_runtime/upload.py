"""File preflight, browser-visible paths and verification on the actual input object."""
from __future__ import annotations

import mimetypes
import ntpath
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from browser_cdp_core import BrowserCdpError, chrome_file_path, is_windows_path, running_in_wsl
from browser_runtime.dom import SelectorGuard, dom_expression, file_state_expression


@dataclass(frozen=True)
class UploadFile:
    local_path: str
    browser_path: str
    name: str
    size: int
    mime_type: str
    exists: bool = True


def prepare_file(value: str, browser_os: str) -> UploadFile:
    windows = is_windows_path(value) or value.startswith('\\\\')
    local = value
    if windows and os.name != 'nt':
        if not running_in_wsl():
            raise BrowserCdpError('Cannot verify Windows path from this host', code='FILE_NOT_FOUND',context={'path':value})
        try:
            local = subprocess.check_output(['wslpath','-u',value],text=True,timeout=5).strip()
        except (OSError,subprocess.SubprocessError) as exc:
            raise BrowserCdpError('Cannot resolve Windows upload file',code='FILE_NOT_FOUND',context={'path':value}) from exc
    path = Path(local).expanduser().resolve()
    if not path.is_file():
        raise BrowserCdpError('Upload path is not a file',code='FILE_NOT_FOUND',context={'path':str(path)})
    if browser_os=='Windows' and not windows and os.name!='nt' and not running_in_wsl():
        raise BrowserCdpError('Local file cannot be mapped to a Windows browser from this host',code='FILE_CONSTRAINT_VIOLATION',context={'path':str(path),'browser_os':browser_os})
    browser_path = value if windows and browser_os=='Windows' else chrome_file_path(str(path)) if browser_os=='Windows' else str(path)
    name = ntpath.basename(browser_path) if browser_os=='Windows' else path.name
    return UploadFile(str(path),browser_path,name,path.stat().st_size,mimetypes.guess_type(name)[0] or '')


def validate_files(files: list[UploadFile], state: dict[str, Any], *, max_file_bytes: int | None = None,
                   max_total_bytes: int | None = None) -> None:
    def reject(message: str) -> None:
        raise BrowserCdpError(message,code='FILE_CONSTRAINT_VIOLATION',context={'input':state})
    if not state['enabled']:
        reject('File input is disabled')
    if not files or (len(files)>1 and not state['multiple']):
        reject('File count violates input multiple constraint')
    accept = [part.strip().casefold() for part in state.get('accept','').split(',') if part.strip()]
    for file in files:
        if max_file_bytes is not None and file.size>max_file_bytes:
            reject('File exceeds maximum size')
        if accept and not any(file.name.casefold().endswith(rule) if rule.startswith('.') else
                              file.mime_type.casefold().startswith(rule[:-1]) if rule.endswith('/*') else
                              file.mime_type.casefold()==rule for rule in accept):
            reject(f'File {file.name!r} violates input accept constraint')
    if max_total_bytes is not None and sum(file.size for file in files)>max_total_bytes:
        reject('Files exceed total size limit')


def upload_files(page: Any, selector: str, paths: list[str], guard: SelectorGuard | None = None, *,
                 check_only: bool = False, max_file_bytes: int | None = None,
                 max_total_bytes: int | None = None) -> dict[str, Any]:
    guard = guard or SelectorGuard()
    platform = str(page.evaluate('navigator.platform'))
    browser_os = 'Windows' if platform.casefold().startswith('win') else 'macOS' if platform.casefold().startswith('mac') else 'Linux'
    before = page.evaluate(file_state_expression(selector,guard))
    files = [prepare_file(path,browser_os) for path in paths]
    validate_files(files,before,max_file_bytes=max_file_bytes,max_total_bytes=max_total_bytes)
    preflight = {'input':before,'browser_os':browser_os,'files':[asdict(file) for file in files]}
    if check_only:
        return {'checked':True,'preflight':preflight}
    # Select afresh, keeping a remote reference only for this single upload.
    remote = page.call('Runtime.evaluate',{'expression':dom_expression(selector,'return el;',guard,mode='file'), 'returnByValue':False})
    if remote.get('exceptionDetails'):
        # Re-evaluate by value to recover the stable JS guard error.
        page.evaluate(file_state_expression(selector,guard))
        raise BrowserCdpError('File input selection failed',code='UPLOAD_VERIFICATION_FAILED')
    object_id = remote.get('result',{}).get('objectId')
    if not object_id:
        raise BrowserCdpError('File input object is unavailable',code='ELEMENT_NOT_FOUND')
    try:
        info = page.call('Runtime.callFunctionOn',{'objectId':object_id,'functionDeclaration':"function(){return {connected:this.isConnected,enabled:!this.disabled,multiple:this.multiple,accept:this.accept,files:[...this.files].map(f=>({name:f.name,size:f.size,type:f.type}))}}",'returnByValue':True})['result']['value']
        if not info['connected']:
            raise BrowserCdpError('File input was replaced before upload',code='ELEMENT_CHANGED_DURING_ACTION')
        validate_files(files,info,max_file_bytes=max_file_bytes,max_total_bytes=max_total_bytes)
        page.call('DOM.setFileInputFiles',{'objectId':object_id,'files':[file.browser_path for file in files]})
        verified = page.call('Runtime.callFunctionOn',{'objectId':object_id,'functionDeclaration':"function(){return {connected:this.isConnected,files:[...this.files].map(f=>({name:f.name,size:f.size,type:f.type}))}}",'returnByValue':True})['result']['value']
        actual = verified['files']
        if len(actual)!=len(files) or any(a['name']!=f.name or a['size']!=f.size for a,f in zip(actual,files)):
            raise BrowserCdpError('Browser file list differs from requested files',code='UPLOAD_VERIFICATION_FAILED',context={'preflight':preflight,'observed':verified})
        try:
            current = page.evaluate(file_state_expression(selector,guard))
        except BrowserCdpError as exc:
            if exc.code not in {'ELEMENT_NOT_FOUND','FILE_INPUT_AMBIGUOUS','ELEMENT_AMBIGUOUS'}:
                raise
            current = {'error_code':exc.code}
        return {'uploaded':True,'files':[file.browser_path for file in files],'preflight':preflight,
                'state':{'count':len(actual),'names':[f['name'] for f in actual],'files':actual},
                'input_rebuilt':not verified['connected'],'current_input':current}
    finally:
        raw = getattr(page,'client',page)
        try:
            raw.call('Runtime.releaseObject',{'objectId':object_id})
        except BrowserCdpError:
            pass
