"""Reusable page connection with a sticky target/navigation lock."""
from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, TextIO
from urllib.parse import urlsplit

from browser_cdp_core import (
    BrowserCdpError, CdpClient, inspect_expression, list_targets, page_client,
    select_target, target_view,
)


def origin(url: str) -> str:
    parsed = urlsplit(url)
    port = parsed.port
    authority = parsed.hostname or ""
    if port and port != {"http": 80, "https": 443}.get(parsed.scheme):
        authority += f":{port}"
    return f"{parsed.scheme}://{authority}"


@dataclass(frozen=True)
class TargetLock:
    target_id: str
    expected_url: str
    expected_origin: str | None = None
    expected_title_regex: str | None = None

    def validate(self, target: dict[str, Any]) -> None:
        actual = str(target.get("url", ""))
        mismatch = str(target.get("id")) != self.target_id or actual != self.expected_url
        mismatch |= self.expected_origin is not None and origin(actual) != self.expected_origin
        mismatch |= self.expected_title_regex is not None and re.search(self.expected_title_regex, str(target.get("title", ""))) is None
        if mismatch:
            raise BrowserCdpError("Locked page identity changed", code="TARGET_LOCK_VIOLATION",
                                  context={"target_id": self.target_id, "expected_url": self.expected_url, "actual_url": actual})


class BrowserSession:
    """One page WebSocket. Never rediscover or navigate a lost locked target."""
    def __init__(self, endpoint: str, *, target: str | dict[str, Any] | None = None,
                 expected_url: str | None = None, expected_origin: str | None = None,
                 expected_title_regex: str | None = None, timeout: float = 15.0):
        self.endpoint = endpoint
        self.selector = target
        self.expected_url = expected_url
        self.expected_origin = expected_origin
        self.expected_title_regex = expected_title_regex
        self.timeout = timeout
        self.client: CdpClient | None = None
        self.lock: TargetLock | None = None
        self.target: dict[str, Any] = {}
        self.frame_id = ""
        self.loader_id = ""
        self.violation: BrowserCdpError | None = None

    def __enter__(self) -> BrowserSession:
        if self.expected_title_regex:
            re.compile(self.expected_title_regex)
        if isinstance(self.selector, dict):
            self.target = self.selector
        else:
            self.target = select_target(list_targets(self.endpoint, timeout=self.timeout), self.selector)
        self.lock = TargetLock(str(self.target["id"]), self.expected_url or str(self.target["url"]),
                               self.expected_origin, self.expected_title_regex)
        self.lock.validate(self.target)
        self.client = page_client(self.target, timeout=self.timeout)
        self.client.__enter__()
        try:
            self.client.call("Page.enable")
            self.client.call("Runtime.enable")
            self.client.call("Network.enable")
            frame = self._frame()
            self.frame_id, self.loader_id = str(frame["id"]), str(frame.get("loaderId", ""))
            self.client.event_listener = self._on_event
            self.check()
        except BaseException:
            self.client.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.client:
            self.client.__exit__(exc_type, exc, tb)

    def _frame(self) -> dict[str, Any]:
        assert self.client
        return self.client.call("Page.getFrameTree")["frameTree"]["frame"]

    def _on_event(self, event: dict[str, Any]) -> None:
        params=event.get('params',{})
        if not self.lock:
            return
        changed=event.get('method')=='Page.navigatedWithinDocument' and params.get('frameId')==self.frame_id and params.get('url')!=self.lock.expected_url
        navigated=event.get('method')=='Page.frameNavigated' and params.get('frame',{}).get('id')==self.frame_id and params['frame'].get('loaderId')!=self.loader_id
        if changed or navigated:
            actual_url=params.get('url') or params.get('frame',{}).get('url')
            self.violation=BrowserCdpError('Navigation occurred during the locked session',code='TARGET_LOCK_VIOLATION' if actual_url!=self.lock.expected_url else 'NAVIGATION_DETECTED',context={'expected_url':self.lock.expected_url,'actual_url':actual_url})

    def check(self, *, discover: bool = False) -> None:
        if self.violation:
            raise self.violation
        if self.client is None or self.lock is None:
            raise BrowserCdpError("Session is not open", code="CDP_UNREACHABLE")
        try:
            if discover:
                targets = list_targets(self.endpoint, timeout=self.timeout)
                target = next((t for t in targets if str(t.get("id")) == self.lock.target_id), None)
                if target is None:
                    raise BrowserCdpError("Locked target was closed", code="TARGET_LOCK_VIOLATION",
                                          context={"target_id": self.lock.target_id, "expected_url": self.lock.expected_url, "actual_url": None})
                self.lock.validate(target)
            frame = self._frame()
            state = self.client.evaluate("({url:location.href,title:document.title})")
            self.lock.validate({"id": self.lock.target_id, **state})
            if (str(frame["id"]) != self.frame_id or str(frame.get("loaderId", "")) != self.loader_id
                    or str(frame.get("url", "")) != self.lock.expected_url):
                raise BrowserCdpError("Main frame/document changed", code="NAVIGATION_DETECTED", context={"frame": frame})
            for event in self.client._events:
                params = event.get("params", {})
                changed = event.get("method") == "Page.navigatedWithinDocument" and params.get("frameId") == self.frame_id and params.get("url") != self.lock.expected_url
                navigated = event.get("method") == "Page.frameNavigated" and params.get("frame", {}).get("id") == self.frame_id and params["frame"].get("loaderId") != self.loader_id
                if changed or navigated:
                    raise BrowserCdpError("Navigation occurred during the locked session", code="NAVIGATION_DETECTED")
        except BrowserCdpError as exc:
            if exc.code in {"TARGET_LOCK_VIOLATION", "NAVIGATION_DETECTED", "CDP_UNREACHABLE"}:
                self.violation = exc
            raise

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.check()
        assert self.client
        result = self.client.call(method, params)
        self.check()
        return result

    def evaluate(self, expression: str, *, await_promise: bool = False) -> Any:
        self.check()
        assert self.client and self.lock
        # Enforce the URL again in the same JS task as the caller's expression.
        guard = json.dumps(self.lock.expected_url)
        wrapped = f"(() => {{ if(location.href !== {guard}) throw new Error('BROWSER_ERROR:' + JSON.stringify({{error_code:'TARGET_LOCK_VIOLATION',message:'Page URL changed',context:{{actual_url:location.href}}}})); return (0,eval)({json.dumps(expression)}); }})()"
        try:
            result = self.client.evaluate(wrapped, await_promise=await_promise)
        except BrowserCdpError:
            self.check()
            raise
        self.check()
        return result

    def collect_events(self, duration: float) -> list[dict[str, Any]]:
        self.check()
        assert self.client
        events = self.client.collect_events(duration)
        # Check navigation before removing events from the lock's view.
        self.client._events = events
        self.check()
        self.client._events = []
        return events

    def execute(self, op: str, **options: Any) -> dict[str, Any]:
        started=time.monotonic()
        try:
            self.check(discover=True)
            result = self._execute(op, options)
            self.check()
            return result
        except BrowserCdpError as exc:
            if options.get("evidence_on_error"):
                from browser_runtime.evidence import capture_evidence
                exc.context["evidence_dir"]=capture_evidence(self,op,options,exc,time.monotonic()-started)
            raise

    def _execute(self, op: str, options: dict[str, Any]) -> dict[str, Any]:
        if op=="focus":
            self.call("Page.bringToFront")
            return {"focused":True,"target":target_view(self.target)}
        if op in {"network","resolve-artifact","browser-fetch"}:
            from browser_runtime.network import observe_network, resolve_artifact, browser_fetch
            from browser_runtime.dom import SelectorGuard
            if op=="network":result=observe_network(self,options)
            elif op=="resolve-artifact":result=resolve_artifact(self,options["selector"],SelectorGuard.from_options(options))
            else:result=browser_fetch(self,options["url"],max_bytes=options.get("max_bytes",20*1024*1024),timeout=options.get("timeout",self.timeout))
            return {"target":target_view(self.target),**result}
        if op in {"screenshot","snapshot"}:
            from browser_runtime.evidence import screenshot, snapshot
            from browser_runtime.dom import SelectorGuard
            guard=SelectorGuard.from_options(options)
            result=screenshot(self,options["output"],options.get("selector"),guard) if op=="screenshot" else snapshot(self,options["selector"],guard,max_chars=options.get("max_chars",10000))
            return {"target":target_view(self.target),**result}
        if op in {"wait","wait-new","wait-transition","wait-mutation","elements"}:
            from browser_runtime.waits import wait_condition, observation_expression
            if op == "elements":
                return {"target":target_view(self.target),"value":self.evaluate(observation_expression(options["selector"],options.get("within"),options.get("attributes"),options.get("identity_attribute")))}
            kind={"wait-new":"new","wait-transition":"transition","wait-mutation":"mutation"}.get(op,"stable" if options.get("dom_stable") else "condition")
            if options.get("dom_stable"): options["selector"]=options["dom_stable"]
            return {"target":target_view(self.target),**wait_condition(self,kind,options)}
        if op == "upload":
            from browser_runtime.upload import upload_files
            from browser_runtime.dom import SelectorGuard
            return {"target":target_view(self.target),**upload_files(self,str(options["selector"]),options["files"],SelectorGuard.from_options(options),check_only=bool(options.get("check_only",False)),max_file_bytes=options.get("max_file_bytes"),max_total_bytes=options.get("max_total_bytes"))}
        if op in {"click", "type", "fill"}:
            from browser_runtime.actions import pointer_click, type_text, fill_native
            from browser_runtime.dom import SelectorGuard
            guard = SelectorGuard.from_options(options)
            selector = str(options["selector"])
            if op == "click":
                action = pointer_click(self,selector,guard,allow_submit=bool(options.get("allow_submit",False)))
            elif op == "type":
                action = type_text(self,selector,str(options["value"]),guard,verify=str(options.get("verify","exact")))
            else:
                action = fill_native(self,selector,str(options["value"]),guard)
            return {"target":target_view(self.target),**action}
        if op == "inspect":
            from browser_runtime.dom import scope_expression
            value = self.evaluate(scope_expression(inspect_expression(int(options.get("text_limit", 12000)), all_controls=bool(options.get("all_controls", False))), options.get("within")))
        elif op == "title":
            value = self.evaluate("document.title")
        elif op == "text":
            limit = max(0, int(options.get("limit", 20000)))
            from browser_runtime.dom import scope_expression
            value = self.evaluate(scope_expression(f"(() => {{ const t=document.body?.innerText||''; return {{text:t.slice(0,{limit}),length:t.length,truncated:t.length>{limit}}}; }})()",options.get("within")))
        elif op == "eval":
            value = self.evaluate(str(options["expression"]), await_promise=bool(options.get("await_promise", False)))
        elif op == "call":
            return {"target": target_view(self.target), "method": options["method"], "result": self.call(options["method"], options.get("params", {}))}
        else:
            raise BrowserCdpError(f"Unsupported session operation: {op}", code="INVALID_ARGUMENT")
        return {"target": target_view(self.target), "value": value}


def serve_session(page: BrowserSession, source: TextIO, sink: TextIO, *, evidence_on_error: bool = False) -> None:
    """Exactly one JSONL response per input line; command failures keep the stream open."""
    for line in source:
        request_id: Any = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise BrowserCdpError("Session request must be an object")
            request_id = request.get("id")
            op = request.pop("op")
            request.pop("id", None)
            request.setdefault("evidence_on_error",evidence_on_error)
            result = page.execute(op, **request)
            response = {"id": request_id, "ok": True, "result": result}
        except BrowserCdpError as exc:
            response = {"id": request_id, **exc.as_dict()}
        except (ValueError, KeyError, TypeError, OSError) as exc:
            response = {"id": request_id, **BrowserCdpError(str(exc)).as_dict()}
        sink.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
        sink.flush()


@contextmanager
def locked_page(args: Any, target: dict[str, Any]) -> Iterator[BrowserSession | CdpClient]:
    # Legacy explicit navigation and URL waits intentionally follow URL changes.
    legacy_navigation = (getattr(args, "command", "") == "network" and getattr(args, "navigate", None)) or (getattr(args, "command", "") == "wait" and getattr(args, "url_contains", None))
    if legacy_navigation and not getattr(args, "expected_url", None):
        with page_client(target, timeout=args.timeout) as client:
            yield client
        return
    with BrowserSession(args.endpoint, target=target, timeout=args.timeout,
                        expected_url=getattr(args, "expected_url", None),
                        expected_origin=getattr(args, "expected_origin", None),
                        expected_title_regex=getattr(args, "expected_title_regex", None)) as page:
        page.check(discover=True)
        started=time.monotonic()
        try:
            yield page
        except BrowserCdpError as exc:
            if getattr(args,"evidence_on_error",False):
                from browser_runtime.evidence import capture_evidence
                exc.context["evidence_dir"]=capture_evidence(page,args.command,vars(args),exc,time.monotonic()-started)
            raise
