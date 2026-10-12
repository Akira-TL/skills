"""Guarded real pointer/text interactions; no synthetic DOM click."""
from __future__ import annotations

import json
from typing import Any

from browser_cdp_core import BrowserCdpError, replace_focused_text
from browser_runtime.dom import SelectorGuard, dom_expression, state_expression


def prepare_point(page: Any, selector: str, guard: SelectorGuard, *, allow_submit: bool = False,
                  require_text: bool = False) -> dict[str, Any]:
    body = """
 el.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
 await new Promise(resolve=>requestAnimationFrame(resolve));
 el=select(selector,guard);
 if(el.disabled) fail('ELEMENT_NOT_VISIBLE','Target is disabled');
 const tag=el.tagName.toLowerCase(),type=(el.type||'').toLowerCase();
 if(el.form && ((tag==='button' && (!type||type==='submit'))||(tag==='input'&&type==='submit')) && !ALLOW_SUBMIT) fail('SUBMIT_NOT_AUTHORIZED','Submit-like click needs --allow-submit');
 if(REQUIRE_TEXT){
   if(type==='password') fail('INPUT_VERIFICATION_FAILED','Password entry remains a human boundary');
   if(el.readOnly || !((tag==='input'&&['','text','search','email','tel','url','number'].includes(type))||tag==='textarea'||el.isContentEditable)) fail('INPUT_VERIFICATION_FAILED','Target does not accept text input');
 }
 const fp=fingerprint(el), x=fp.rect.x+fp.rect.width/2,y=fp.rect.y+fp.rect.height/2;
 const hit=document.elementFromPoint(x,y);
 if(!hit || !(hit===el||el.contains(hit))) fail('ELEMENT_OCCLUDED','Target center is blocked',{fingerprint:fp,blocker:hit?.tagName});
 return {...fp,x,y};
""".replace('ALLOW_SUBMIT', str(allow_submit).lower()).replace('REQUIRE_TEXT', str(require_text).lower())
    return page.evaluate(dom_expression(selector, body, guard, asynchronous=True), await_promise=True)


def assert_same(page: Any, selector: str, guard: SelectorGuard, point: dict[str, Any]) -> None:
    body = f"""
 const expected={json.dumps(point, ensure_ascii=False)},actual=fingerprint(el);
 const same=actual.identity===expected.identity && actual.tag===expected.tag && actual.text===expected.text && actual.aria_label===expected.aria_label && actual.role===expected.role && JSON.stringify(actual.ancestor_ids)===JSON.stringify(expected.ancestor_ids) && JSON.stringify(actual.rect)===JSON.stringify(expected.rect);
 const hit=document.elementFromPoint(expected.x,expected.y);
 if(!same) fail('ELEMENT_CHANGED_DURING_ACTION','Target changed during pointer action',{{expected,actual}});
 if(!hit||!(hit===el||el.contains(hit))) fail('ELEMENT_OCCLUDED','Target became blocked',{{actual}});
 return actual;
"""
    try:
        page.evaluate(dom_expression(selector, body, guard))
    except BrowserCdpError as exc:
        if exc.code in {'ELEMENT_NOT_FOUND','ELEMENT_NOT_VISIBLE','ELEMENT_AMBIGUOUS'}:
            raise BrowserCdpError('Target disappeared or became ambiguous during action', code='ELEMENT_CHANGED_DURING_ACTION', context={'fingerprint':point}) from exc
        raise


def pointer_click(page: Any, selector: str, guard: SelectorGuard | None = None, *,
                  allow_submit: bool = False, require_text: bool = False) -> dict[str, Any]:
    guard = guard or SelectorGuard()
    point = prepare_point(page, selector, guard, allow_submit=allow_submit, require_text=require_text)
    coordinates = {'x':point['x'],'y':point['y']}
    page.call('Input.dispatchMouseEvent', {'type':'mouseMoved',**coordinates})
    assert_same(page,selector,guard,point)
    pressed = False
    try:
        page.call('Input.dispatchMouseEvent', {'type':'mousePressed',**coordinates,'button':'left','buttons':1,'clickCount':1})
        pressed = True
        assert_same(page,selector,guard,point)
        page.call('Input.dispatchMouseEvent', {'type':'mouseReleased',**coordinates,'button':'left','buttons':0,'clickCount':1})
        pressed = False
    finally:
        if pressed:
            # Cancel at a point outside the page, even when the page lock failed.
            raw = getattr(page, 'client', page)
            try:
                raw.call('Input.dispatchMouseEvent', {'type':'mouseReleased','x':-1,'y':-1,'button':'left','buttons':0,'clickCount':1})
            except BrowserCdpError:
                pass
    # Removing a modal/button in its click handler is a legitimate outcome.
    after = page.evaluate(f"(() => {{const el=document.querySelector({json.dumps(selector)});return {{href:location.href,target_present:!!el}};}})()")
    return {'clicked':True,'interaction':point,'after':after}


def type_text(page: Any, selector: str, value: str, guard: SelectorGuard | None = None,
              *, verify: str = 'exact') -> dict[str, Any]:
    if verify not in {'exact','contains','none'}:
        raise BrowserCdpError('Unknown input verification mode')
    guard = guard or SelectorGuard()
    before = page.evaluate(state_expression(selector,guard))
    click = pointer_click(page,selector,guard,require_text=True)
    focused = page.evaluate(state_expression(selector,guard))
    if not focused['focused']:
        raise BrowserCdpError('Pointer click did not focus text target',code='FOCUS_FAILED',context={'state':focused})
    # Text guards apply before editing; identity/focus apply afterwards.
    after_guard = SelectorGuard(within=guard.within,expect_role=guard.expect_role,
                                expect_count=guard.expect_count,allow_multiple=guard.allow_multiple)
    class FocusedInput:
        def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
            current=page.evaluate(state_expression(selector,after_guard))
            if not current['focused'] or current['identity']!=focused['identity']:
                raise BrowserCdpError('Input focus or target changed before keyboard event',code='FOCUS_FAILED',context={'state':current})
            return page.call(method,params)
    replace_focused_text(FocusedInput(),value)
    state = page.evaluate(state_expression(selector,after_guard))
    matched = state['value'] == value if verify=='exact' else value in state['value'] if verify=='contains' else True
    if not matched or not state['focused'] or state['identity'] != focused['identity'] or state['aria_invalid']=='true':
        raise BrowserCdpError('Input post-condition failed',code='INPUT_VERIFICATION_FAILED',context={'before':before,'after':state,'verify':verify})
    return {'typed':True,'before':before,'state':state,'interaction':click['interaction'],'navigation':False}


def fill_native(page: Any, selector: str, value: str, guard: SelectorGuard | None = None) -> dict[str, Any]:
    body = f"""
 const nextValue={json.dumps(value)};
 if(el.disabled||el.readOnly||el.isContentEditable||['checkbox','radio','file','password'].includes(el.type)) fail('INPUT_VERIFICATION_FAILED','Use real interaction for this control');
 const prototype=el.tagName==='INPUT'?HTMLInputElement.prototype:el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:null;
 if(prototype) Object.getOwnPropertyDescriptor(prototype,'value').set.call(el,nextValue);
 else if(el.tagName==='SELECT') el.value=nextValue;
 else fail('INPUT_VERIFICATION_FAILED','Unsupported native fill target');
 el.dispatchEvent(new Event('input',{{bubbles:true}}));el.dispatchEvent(new Event('change',{{bubbles:true}}));
 return {{filled:true,...state(el)}};
"""
    return {'value':page.evaluate(dom_expression(selector,body,guard))}
