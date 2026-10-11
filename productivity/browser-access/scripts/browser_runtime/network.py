"""Safe network predicates and page-authorized artifact primitives."""
from __future__ import annotations

import base64
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from browser_cdp_core import BrowserCdpError, summarize_network_events
from browser_runtime.dom import SelectorGuard, dom_expression


def status_matches(actual: int | float | None, wanted: str) -> bool:
    if re.fullmatch(r'[1-5]xx',wanted):
        return actual is not None and int(actual)//100==int(wanted[0])
    if not re.fullmatch(r'\d{3}(,\d{3})*',wanted):
        raise BrowserCdpError('Status predicate must be 2xx or comma-separated codes')
    return actual is not None and int(actual) in {int(code) for code in wanted.split(',')}


def observe_network(page: Any, options: dict[str, Any]) -> dict[str, Any]:
    mode=options.get('mode','capture')
    if mode not in {'capture','wait-response','wait-request','wait-idle'}:
        raise BrowserCdpError('Unknown network mode')
    timeout=float(options.get('timeout',getattr(page,'timeout',15)))
    try:pattern=re.compile(options.get('url_regex') or '.*')
    except re.error as exc:raise BrowserCdpError('Invalid network URL regular expression',context={'pattern':options.get('url_regex')}) from exc
    status=str(options.get('status','2xx'))
    status_matches(None,status)
    duration=max(0,float(options.get('duration',3)))
    page.call('Network.enable')
    records: list[dict[str, Any]]=[]
    events: list[dict[str, Any]]=[]
    inflight: dict[str,str]={}
    activity=time.monotonic()
    started=activity
    trigger_result=None
    if options.get('click') or options.get('navigate'):
        # Discard earlier activity before this explicit trigger.
        page.collect_events(0)
        if options.get('click'):
            from browser_runtime.actions import pointer_click
            trigger_result=pointer_click(page,options['click'],SelectorGuard(within=options.get('within')),allow_submit=bool(options.get('allow_submit',False)))['interaction']
        else:
            trigger_result=page.call('Page.navigate',{'url':options['navigate']})
    while True:
        new=page.collect_events(min(0.05,max(0,duration if mode=='capture' else timeout)))
        events.extend(new)
        events=events[-5000:]
        for event in new:
            params=event.get('params',{})
            request_id=str(params.get('requestId',''))
            url=str(params.get('request',params.get('response',{})).get('url',''))
            if event.get('method')=='Network.requestWillBeSent' and pattern.search(url):
                inflight[request_id]=url;activity=time.monotonic()
            elif event.get('method') in {'Network.loadingFinished','Network.loadingFailed'} and request_id in inflight:
                inflight.pop(request_id);activity=time.monotonic()
            elif event.get('method')=='Network.responseReceived' and pattern.search(url):
                activity=time.monotonic()
        raw=getattr(page,'client',page)
        if hasattr(raw,'_network_requests'):
            inflight={key:url for key,url in raw._network_requests.items() if pattern.search(url)}
            stamps=[stamp for url,stamp in raw._network_activity.items() if pattern.search(url)]
            if stamps:activity=max(activity,max(stamps))
        records=[record for record in summarize_network_events(events,url_contains=options.get('url_contains')) if pattern.search(str(record.get('url','')))]
        elapsed=time.monotonic()-started
        matched=[r for r in records if status_matches(r.get('status'),status)] if mode=='wait-response' else [r for r in records if r.get('method')]
        met = elapsed>=duration if mode=='capture' else bool(matched) if mode in {'wait-response','wait-request'} else not inflight and (time.monotonic()-activity)*1000>=float(options.get('idle_ms',500))
        if met:
            limit=max(0,min(int(options.get('max_results',200)),1000))
            chosen=matched if mode in {'wait-response','wait-request'} else records
            return {'trigger':trigger_result,'mode':mode,'met':True,'elapsedSeconds':round(elapsed,3),'eventCount':len(events),'recordCount':len(chosen),'returnedRecordCount':min(len(chosen),limit),'records':chosen[:limit],'inflight_count':len(inflight)}
        if elapsed>=timeout:
            raise BrowserCdpError('Network condition timed out',code='WAIT_TIMEOUT',context={'condition':{'network':mode,'url_regex':pattern.pattern,'status':status},'elapsed':round(elapsed,3),'last_observed':records[-20:],'mutation_count':0,'inflight_count':len(inflight)})


def resolve_artifact(page: Any, selector: str, guard: SelectorGuard | None = None) -> dict[str, Any]:
    return page.evaluate(dom_expression(selector,"""
 const raw=el.getAttribute('data-safe-src')||el.currentSrc||el.href||el.src||el.getAttribute('data')||'';
 if(!raw) fail('ARTIFACT_NOT_FOUND','Element has no artifact URL');
 const url=new URL(raw,location.href);
 if(!['http:','https:','blob:','data:'].includes(url.protocol)) fail('ARTIFACT_NOT_FOUND','Unsupported artifact URL scheme');
 const name=el.getAttribute('download')||decodeURIComponent(url.pathname.split('/').pop()||'artifact');
 return {url:url.href,href:el.href||null,data_safe_src:el.getAttribute('data-safe-src'),currentSrc:el.currentSrc||null,content_type_hint:el.getAttribute('type')||null,suggested_filename:name,referer:location.href};
""",guard,mode='all'))


def browser_fetch(page: Any, url: str, *, max_bytes: int = 20*1024*1024, timeout: float = 15) -> dict[str, Any]:
    if urlsplit(url).scheme not in {'http','https','blob','data'} or max_bytes<=0:
        raise BrowserCdpError('Fetch requires an allowed URL and positive byte bound')
    max_bytes=min(max_bytes,100*1024*1024)
    body=f"""(async()=>{{
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),{max(1,timeout)*1000});
 try{{const response=await fetch({json.dumps(url)},{{credentials:'include',signal:controller.signal}});
 if(!response.ok) throw new Error('BROWSER_ERROR:'+JSON.stringify({{error_code:'FETCH_FAILED',message:'HTTP '+response.status,context:{{status:response.status}}}}));
 const reader=response.body.getReader(),chunks=[];let size=0;
 while(true){{const chunk=await reader.read();if(chunk.done)break;size+=chunk.value.length;if(size>{max_bytes}){{await reader.cancel();throw new Error('BROWSER_ERROR:'+JSON.stringify({{error_code:'ARTIFACT_TOO_LARGE',message:'Fetch exceeds byte bound'}}));}}chunks.push(chunk.value);}}
 let binary='';for(const chunk of chunks)for(let i=0;i<chunk.length;i+=8192)binary+=String.fromCharCode(...chunk.subarray(i,i+8192));
 return {{base64:btoa(binary),bytes:size,url:response.url,content_type:response.headers.get('content-type')}};
 }}finally{{clearTimeout(timer);}}
}})()"""
    result=page.evaluate(body,await_promise=True)
    suffix=Path(urlsplit(url).path).suffix
    if not re.fullmatch(r'\.[A-Za-z0-9]{1,8}',suffix):suffix='.bin'
    with tempfile.NamedTemporaryFile(prefix='browser-artifact-',suffix=suffix,delete=False) as file:
        file.write(base64.b64decode(result.pop('base64'),validate=True))
        result['output']=file.name
    return result
