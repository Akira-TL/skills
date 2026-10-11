"""Shared scoped selectors, element identities and bounded state readers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SelectorGuard:
    within: str | None = None
    expect_text: str | None = None
    expect_role: str | None = None
    expect_count: int = 1
    allow_multiple: bool = False
    predicate: str | None = None

    def __post_init__(self) -> None:
        from browser_cdp_core import BrowserCdpError
        if type(self.expect_count) is not int or self.expect_count < 1:
            raise BrowserCdpError("expect_count must be a positive integer")
        for value in (self.within,self.expect_text,self.expect_role,self.predicate):
            if value is not None and not isinstance(value,str):
                raise BrowserCdpError("Selector guard values must be strings")

    @classmethod
    def from_options(cls, options: dict[str, Any]) -> SelectorGuard:
        return cls(**{key: options[key] for key in cls.__dataclass_fields__ if key in options})


DOM_HELPERS = r"""
const fail = (error_code, message, context={}) => { throw new Error('BROWSER_ERROR:'+JSON.stringify({error_code,message,context})); };
const storeKey = Symbol.for('browser-access.element-identities');
const identities = globalThis[storeKey] ||= {nodes:new WeakMap(), next:1};
const identity = el => { if(!identities.nodes.has(el)) identities.nodes.set(el,identities.next++); return identities.nodes.get(el); };
const visible = el => {const r=el.getBoundingClientRect(), s=getComputedStyle(el); return s.display!=='none' && s.visibility!=='hidden' && s.visibility!=='collapse' && r.width>0 && r.height>0;};
const text = el => (['INPUT','TEXTAREA','SELECT'].includes(el.tagName) ? el.value : (el.innerText ?? el.textContent ?? '')).trim();
const role = el => el.getAttribute('role') || ({BUTTON:'button',TEXTAREA:'textbox',SELECT:'combobox',A:el.href?'link':''}[el.tagName]) || (el.isContentEditable?'textbox':el.tagName==='INPUT'?({checkbox:'checkbox',radio:'radio'}[el.type]||'textbox'):'');
const ancestors = el => {const out=[]; for(let p=el.parentElement;p && out.length<12;p=p.parentElement) if(p.id) out.push(p.id); return out;};
const fingerprint = el => {const r=el.getBoundingClientRect(); return {identity:identity(el),tag:el.tagName,text:text(el).slice(0,300),aria_label:el.getAttribute('aria-label'),role:role(el),ancestor_ids:ancestors(el),rect:{x:r.x,y:r.y,width:r.width,height:r.height},href:location.href};};
const state = el => ({...fingerprint(el),value:el.isContentEditable?el.innerText:(el.value??el.innerText??''),focused:document.activeElement===el||el.contains(document.activeElement),contenteditable:el.isContentEditable,aria_invalid:el.getAttribute('aria-invalid'),disabled:!!el.disabled});
const select = (selector, guard, mode='visible') => {
  let root=document;
  if(guard.within){const roots=[...document.querySelectorAll(guard.within)]; if(roots.length!==1) fail(roots.length?'ELEMENT_AMBIGUOUS':'ELEMENT_NOT_FOUND','Scope must match exactly one ancestor',{within:guard.within,count:roots.length}); root=roots[0];}
  let found=[...root.querySelectorAll(selector)];
  if(mode==='visible'){const shown=found.filter(visible); if(found.length && !shown.length) fail('ELEMENT_NOT_VISIBLE','No visible target',{selector}); found=shown;}
  if(mode==='file') found=found.filter(el=>el.tagName==='INPUT'&&el.type==='file');
  if(guard.expect_text!==null && guard.expect_text!==undefined) found=found.filter(el=>text(el)===guard.expect_text);
  if(guard.expect_role) found=found.filter(el=>role(el)===guard.expect_role);
  if(guard.predicate) found=found.filter(el=>(new Function('el','return ('+guard.predicate+')'))(el));
  if(!found.length) fail('ELEMENT_NOT_FOUND','No element satisfies selector guards',{selector,guard});
  if(found.length!==guard.expect_count || (found.length>1&&!guard.allow_multiple)) fail(mode==='file'?'FILE_INPUT_AMBIGUOUS':'ELEMENT_AMBIGUOUS','Selector count violates guard',{selector,count:found.length,expected:guard.expect_count});
  return found[0];
};
"""


def dom_expression(selector: str, body: str, guard: SelectorGuard | None = None,
                   *, mode: str = "visible", asynchronous: bool = False) -> str:
    guard = guard or SelectorGuard()
    return f"({'async ' if asynchronous else ''}() => {{\n{DOM_HELPERS}\nconst selector={json.dumps(selector, ensure_ascii=False)},guard={json.dumps(asdict(guard), ensure_ascii=False)};\nlet el=select(selector,guard,{json.dumps(mode)});\n{body}\n}})()"


def state_expression(selector: str, guard: SelectorGuard | None = None) -> str:
    return dom_expression(selector, "return state(el);", guard)


def file_state_expression(selector: str, guard: SelectorGuard | None = None) -> str:
    return dom_expression(selector, "return {...fingerprint(el),enabled:!el.disabled,multiple:el.multiple,accept:el.accept,files:[...el.files].map(f=>({name:f.name,size:f.size,type:f.type}))};", guard, mode="file")


def scope_expression(expression: str, within: str | None) -> str:
    if not within:
        return expression
    # Read-only expressions use an explicitly unique ancestor.
    scoped = expression.replace("document.querySelectorAll", "el.querySelectorAll").replace("document.body?.innerText", "el.innerText")
    return dom_expression(within, "return ("+scoped+");", mode="all")
