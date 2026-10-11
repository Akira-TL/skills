"""Inspectable waits with MutationObserver, baselines and bounded observations."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from browser_cdp_core import BrowserCdpError
from browser_runtime.dom import DOM_HELPERS


def observation_expression(selector: str | None, within: str | None = None,
                           attributes: list[str] | None = None) -> str:
    selector_js = json.dumps(selector)
    within_js = json.dumps(within)
    attrs_js = json.dumps(attributes or ['class','aria-busy','aria-invalid','data-state'])
    return f"""(() => {{ {DOM_HELPERS}
 const within={within_js}, selector={selector_js};let root=document;
 if(within){{const roots=[...document.querySelectorAll(within)]; if(roots.length>1) fail('ELEMENT_AMBIGUOUS','Wait scope is ambiguous'); if(!roots.length) return [];root=roots[0];}}
 return [...root.querySelectorAll(selector||'body')].slice(0,100).map(el=>({{identity:identity(el),id:el.id,text:(el.innerText||el.textContent||'').slice(0,1000),visible:visible(el),attributes:Object.fromEntries({attrs_js}.map(name=>[name,el.getAttribute(name)]))}}));
}})()"""


def wait_condition(page: Any, kind: str, options: dict[str, Any]) -> dict[str, Any]:
    timeout = float(options.get('timeout',getattr(page,'timeout',15)))
    if timeout<=0:
        raise BrowserCdpError('Wait timeout must be positive')
    poll = max(0.01,float(options.get('poll',0.1)))
    selector,within = options.get('selector'),options.get('within')
    if kind in {'new','transition','stable'} and not selector:
        raise BrowserCdpError('This wait requires a selector')
    observer_key = '__browserAccessWait_'+uuid.uuid4().hex
    key_js = json.dumps(observer_key)
    within_js = json.dumps(within)
    # Observe the document so a scoped container's replacement is observable too.
    page.evaluate(f"""(() => {{const key={key_js};const slot={{count:0,wake:null}};
 const observer=new MutationObserver(records=>{{const root={within_js}?document.querySelector({within_js}):document;
 const count=records.filter(r=>!root||r.target===root||root.contains(r.target)||[...r.addedNodes,...r.removedNodes].some(n=>n===root||n.contains?.(root))).length;
 slot.count+=count;if(count && slot.wake) slot.wake();}});
 observer.observe(document,{{subtree:true,childList:true,characterData:true,attributes:true}});
 slot.observer=observer;globalThis[key]=slot;return true;}})()""")
    started = time.monotonic()
    observation = observation_expression(selector,within,options.get('attributes'))
    baseline = options.get('baseline')
    last: Any = None
    mutation_count = 0
    transitions: list[str] = []
    stable_since = started
    previous = None
    try:
        initial = page.evaluate(observation)
        if baseline is None:
            baseline = [item['identity'] for item in initial]
        elif not isinstance(baseline,list):
            raise BrowserCdpError('New-element baseline must be an identity array')
        if options.get('initial_text') is not None:
            initial_text='\n'.join(item['text'] for item in initial)
            if initial_text != options['initial_text']:
                raise BrowserCdpError('Initial text does not match',code='WAIT_INITIAL_STATE_MISMATCH',context={'last_observed':initial})
        if options.get('click'):
            from browser_runtime.actions import pointer_click
            from browser_runtime.dom import SelectorGuard
            pointer_click(page,options['click'],SelectorGuard(within=options.get('click_within')),allow_submit=bool(options.get('allow_submit',False)))
        while True:
            last = page.evaluate(observation)
            value = '\n'.join(item['text'] for item in last)
            mutation_count = int(page.evaluate(f'globalThis[{key_js}]?.count||0'))
            elapsed = time.monotonic()-started
            met = False
            if kind=='new':
                new=[item for item in last if item['identity'] not in baseline]
                met=bool(new)
                if met: last=new
            elif kind=='stable':
                signature=json.dumps([{key:item[key] for key in ('text','attributes','visible')} for item in last],ensure_ascii=False)
                if signature!=previous:
                    previous,stable_since=signature,time.monotonic()
                met=bool(last) and (time.monotonic()-stable_since)*1000>=float(options.get('stable_ms',500))
            elif kind=='transition':
                if not transitions or transitions[-1]!=value:
                    transitions.append(value)
                complete=options.get('until_expression')
                if not complete:
                    raise BrowserCdpError('Text transition requires until_expression')
                intermediate=options.get('intermediate_text',[])
                met=bool(page.evaluate(f"(() => {{const observed={json.dumps(last,ensure_ascii=False)},value={json.dumps(value,ensure_ascii=False)};return ({complete});}})()")) and all(item in transitions for item in intermediate)
            elif kind=='mutation':
                complete=options.get('until_expression')
                met=mutation_count>0 and (bool(page.evaluate(complete)) if complete else True)
            elif options.get('expression') is not None:
                last=page.evaluate(options['expression']);met=bool(last)
            elif selector:
                met=bool(last)
            elif options.get('text') is not None:
                last=page.evaluate(f"(document.body?.innerText||'').includes({json.dumps(options['text'])})");met=bool(last)
            elif options.get('url_contains') is not None:
                last=page.evaluate(f"location.href.includes({json.dumps(options['url_contains'])})");met=bool(last)
            else:
                raise BrowserCdpError('Wait requires a condition')
            if met:
                return {'met':True,'condition':kind,'elapsedSeconds':round(elapsed,3),'value':last,
                        'last_observed':last,'mutation_count':mutation_count,'baseline':baseline,'transitions':transitions}
            if elapsed>=timeout:
                raise BrowserCdpError('Wait condition timed out',code='WAIT_TIMEOUT',context={
                    'condition':{'kind':kind,'selector':selector,'within':within,'expression':options.get('expression') or options.get('until_expression')},
                    'elapsed':round(elapsed,3),'last_observed':last,'mutation_count':mutation_count,'transitions':transitions})
            delay_ms=min(poll,max(0,timeout-elapsed))*1000
            # Wake on a mutation; timer fallback covers non-DOM conditions.
            page.evaluate(f"new Promise(resolve=>{{const slot=globalThis[{key_js}];const timer=setTimeout(done,{delay_ms});function done(){{clearTimeout(timer);if(slot)slot.wake=null;resolve(true);}}if(slot)slot.wake=done;}})",await_promise=True)
    finally:
        raw = getattr(page,'client',page)
        try:
            raw.evaluate(f"(() => {{globalThis[{key_js}]?.observer.disconnect();delete globalThis[{key_js}];}})()")
        except BrowserCdpError:
            pass
