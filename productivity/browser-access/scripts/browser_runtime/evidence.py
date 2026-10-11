"""Native screenshots, bounded snapshots and temporary failure evidence."""
from __future__ import annotations

import base64
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from browser_cdp_core import BrowserCdpError
from browser_runtime.dom import SelectorGuard, dom_expression


SENSITIVE = re.compile(r'cookie|authorization|password|passwd|token|secret|csrf|otp',re.I)


def redact(value: Any) -> Any:
    if isinstance(value,dict):
        return {key:('[redacted]' if SENSITIVE.search(key) else redact(item)) for key,item in value.items() if key not in {'headers','postData'}}
    if isinstance(value,list):
        return [redact(item) for item in value[:100]]
    if isinstance(value,str):
        value=re.sub(r'(?i)(bearer\s+)[\w.\-]+',r'\1[redacted]',value)
        value=re.sub(r'(?i)((?:cookie|authorization|token|secret|password)\s*[:=]\s*)[^\s,;]+',r'\1[redacted]',value)
        value=re.sub(r'https?://[^\s\"<>]+',lambda m:safe_url(m.group()),value)
        return value[:12000]
    return value


def safe_url(url: str) -> str:
    try:
        parts=urlsplit(url)
        host=parts.netloc.rsplit('@',1)[-1]
        return urlunsplit((parts.scheme,host,parts.path,'',''))
    except ValueError:
        return '[invalid URL]'


def screenshot(page: Any, output: str | Path, selector: str | None = None,
               guard: SelectorGuard | None = None) -> dict[str, Any]:
    params: dict[str, Any]={'format':'png','captureBeyondViewport':False}
    if selector:
        rect=page.evaluate(dom_expression(selector,"el.scrollIntoView({block:'center',behavior:'instant'});await new Promise(resolve=>requestAnimationFrame(resolve));el=select(selector,guard);const r=el.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height};",guard,asynchronous=True),await_promise=True)
        params.update({'clip':{**rect,'scale':1},'captureBeyondViewport':True})
    result=page.call('Page.captureScreenshot',params)
    path=Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(base64.b64decode(result['data'],validate=True))
    return {'output':str(path),'bytes':path.stat().st_size}


def snapshot(page: Any, selector: str, guard: SelectorGuard | None = None,
             *, max_chars: int = 10000) -> dict[str, Any]:
    limit=max(0,min(int(max_chars),100000))
    body=f"""
 const clone=el.cloneNode(true);
 clone.querySelectorAll('script,style,input[type=password],input[type=hidden]').forEach(n=>n.remove());
 for(const node of [clone,...clone.querySelectorAll('*')]){{
   for(const a of [...node.attributes]) if(/cookie|authorization|password|token|secret|csrf|otp/i.test(a.name)||a.name==='value'||a.name.startsWith('on')) node.removeAttribute(a.name);
   if(/password|token|secret|csrf|otp/i.test((node.id||'')+' '+(node.name||''))){{node.textContent='[redacted]';node.removeAttribute('value');}}
 }}
 const html=clone.outerHTML;
 return {{...fingerprint(el),outerHTML:html.slice(0,{limit}),html_length:html.length,truncated:html.length>{limit},visible:visible(el),visibility:getComputedStyle(el).visibility,child_controls:[...el.querySelectorAll('input,textarea,select,button,[role]')].slice(0,100).map(n=>({{tag:n.tagName,id:n.id,role:role(n),visible:visible(n)}}))}};
"""
    return page.evaluate(dom_expression(selector,body,guard,mode='all'))


EVIDENCE_EXPRESSION = """(() => {
 const sensitive=el=>/password|passwd|token|secret|cookie|authorization|csrf|otp/i.test((el.id||'')+' '+(el.name||'')+' '+(el.type||''));
 const texts=[];if(document.body){const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode())&&texts.join('').length<12000){let el=node.parentElement;if(!el||el.closest('script,style,input,textarea,[contenteditable]'))continue;let shown=true;for(let parent=el;parent;parent=parent.parentElement){const style=getComputedStyle(parent);if(style.display==='none'||style.visibility==='hidden'){shown=false;break;}}if(shown&&el.getClientRects().length)texts.push(sensitive(el)?'[redacted]':node.textContent);}}
 const controls=[...document.querySelectorAll('input,textarea,select,button,[contenteditable],[role]')].filter(el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return el.type==='file'||(r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none');}).slice(0,100).map(el=>({tag:el.tagName,id:el.id,name:el.name,type:el.type||'',role:el.getAttribute('role'),text:sensitive(el)?'[redacted]':(el.tagName==='BUTTON'?el.innerText:'').slice(0,300),aria_label:el.getAttribute('aria-label')}));
 return {visible_text:texts.join(' ').slice(0,12000),controls};
})()"""


def capture_evidence(page: Any, action: str, options: dict[str, Any], error: BrowserCdpError,
                     elapsed: float) -> str | None:
    try:
        return _capture_evidence(page,action,options,error,elapsed)
    except Exception as exc:
        error.context['evidence_capture_error']=str(redact(str(exc)))
        return None


def _capture_evidence(page: Any, action: str, options: dict[str, Any], error: BrowserCdpError,
                      elapsed: float) -> str:
    root=Path(tempfile.gettempdir())/'browser-evidence'
    root.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'),dir=root))
    meta={'action':action,'selector':options.get('selector'),'expected_guard':{key:options.get(key) for key in ('within','expect_text','expect_role','expect_count')},
          'target_id':getattr(page,'target',{}).get('id'),'url':getattr(page,'target',{}).get('url'),
          'error_code':error.code,'elapsed':round(elapsed,3),'element_fingerprint':error.context.get('fingerprint') or error.context.get('expected') or error.context.get('after'),
          'capture_errors':[]}
    def save(name: str,value: Any) -> None:
        (directory/name).write_text(json.dumps(redact(value),ensure_ascii=False,indent=2),encoding='utf-8')
    save('target.json',getattr(page,'target',{}))
    try:
        if hasattr(page,'check'):page.check()
        raw=getattr(page,'client',page)
        observed=raw.evaluate(EVIDENCE_EXPRESSION)
        (directory/'visible-text.txt').write_text(str(redact(observed['visible_text'])),encoding='utf-8')
        save('controls.json',observed['controls'])
        console=[]
        for event in getattr(raw,'_events',[]):
            if event.get('method')=='Runtime.exceptionThrown':
                details=event.get('params',{}).get('exceptionDetails',{})
                console.append({'text':details.get('text'),'description':details.get('exception',{}).get('description')})
            elif event.get('method')=='Runtime.consoleAPICalled' and event.get('params',{}).get('type')=='error':
                console.append({'arguments':[item.get('value') or item.get('description') for item in event['params'].get('args',[])][:20]})
        save('console-errors.json',console[-100:])
        # Reversible masking keeps sensitive form controls out of failure screenshots.
        raw.evaluate("(() => {globalThis.__browserAccessMasks=[...document.querySelectorAll('input,textarea,[contenteditable]')].map(el=>[el,el.style.filter]);for(const [el] of globalThis.__browserAccessMasks)el.style.filter='blur(12px)';})()")
        try:
            screenshot(page,directory/'screenshot.png')
        finally:
            raw.evaluate("(() => {for(const [el,filter] of globalThis.__browserAccessMasks||[])el.style.filter=filter;delete globalThis.__browserAccessMasks;})()")
    except (BrowserCdpError,OSError,ValueError) as exc:
        meta['capture_errors'].append(str(exc))
    save('meta.json',meta)
    return str(directory)
