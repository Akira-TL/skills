#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "websocket-client>=1.8,<2",
# ]
# ///
"""Command-line entry point for browser-access Chrome DevTools Protocol control."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Installed Skill payloads can be immutable Store projections.
sys.dont_write_bytecode = True

from browser_cdp_lifecycle import (
    BrowserConfig, browser_status, ensure_browser, ensure_then_targets, selected_target,
)
from browser_runtime.network import observe_network, resolve_artifact, browser_fetch
from browser_runtime.waits import wait_condition, observation_expression
from browser_runtime.upload import upload_files
from browser_runtime.actions import pointer_click, type_text, fill_native
from browser_runtime.dom import SelectorGuard, dom_expression, scope_expression
from browser_session import TargetLock, BrowserSession, locked_page, serve_session
from browser_cdp_profiles import DEFAULT_CONFIG_PATH, load_profiles, resolve_profile, save_profile
from browser_cdp_core import (
    DEFAULT_ENDPOINT,
    BrowserCdpError,
    CdpProtocolError,
    browser_client,
    chrome_file_path,
    dispatch_primary_click,
    emit,
    fill_expression,
    inspect_expression,
    interaction_point_expression,
    list_targets,
    page_client,
    page_targets,
    read_expression,
    read_json_object,
    require_browser,
    replace_focused_text,
    summarize_network_events,
    target_state_expression,
    target_view,
    wait_ready,
    validate_timeout,
)

class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BrowserCdpError(message, code="INVALID_ARGUMENT")

def add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-url", help="exact locked page URL")
    parser.add_argument("--expected-origin", help="optional locked origin")
    parser.add_argument("--expected-title-regex", help="optional title constraint")
    parser.add_argument(
        "--target",
        help="page target: exact ID, unique ID prefix, unique title fragment, or unique URL fragment",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Fast deterministic control surface for browser-access's WSL -> Windows Chrome CDP adapter"
    )
    parser.add_argument("--endpoint", help=f"CDP HTTP endpoint (default: {DEFAULT_ENDPOINT})")
    parser.add_argument("--profile", help="saved dedicated configuration name (default: agent-browser)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help=f"host-local named configuration file (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("--user-data-dir", help="dedicated persistent Chrome data directory (absolute Windows path)")
    parser.add_argument("--profile-directory", help="Chrome profile subdirectory within the dedicated data directory (default: Default)")
    parser.add_argument("--timeout", type=float, default=15.0, help="operation timeout in seconds (default: 15)")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="probe the CDP endpoint without launching Chrome")
    sub.add_parser("ensure", help="reuse or launch the selected dedicated persistent Chrome")
    sub.add_parser("tabs", help="list page targets only")
    sub.add_parser("profiles", help="list dedicated saved configurations without connecting to Chrome")
    save_parser = sub.add_parser("profile-save", help="save a new dedicated configuration without launching Chrome")
    save_parser.add_argument("name", help="unique dedicated configuration name, such as chatgpt")

    open_parser = sub.add_parser("open", help="open a URL in a new tab in the existing Agent Chrome")
    open_parser.add_argument("url")

    focus_parser = sub.add_parser("focus", help="activate a selected page target")
    add_target_argument(focus_parser)

    nav_parser = sub.add_parser("navigate", help="navigate a selected page and wait for document readiness")
    add_target_argument(nav_parser)
    nav_parser.add_argument("url")

    title_parser = sub.add_parser("title", help="read document.title from a selected page")
    add_target_argument(title_parser)

    text_parser = sub.add_parser("text", help="read visible body text from a selected page")
    add_target_argument(text_parser)
    text_parser.add_argument("--limit", type=int, default=20000, help="maximum returned characters (default: 20000)")

    inspect_parser = sub.add_parser("inspect", help="return page text plus structured form/control metadata")
    add_target_argument(inspect_parser)
    inspect_parser.add_argument("--text-limit", type=int, default=12000, help="maximum body text characters")
    inspect_parser.add_argument("--all-controls", action="store_true", help="include hidden controls as well as visible/file controls")

    eval_parser = sub.add_parser("eval", help="evaluate page JavaScript; pass '-' to read the expression from stdin")
    add_target_argument(eval_parser)
    eval_parser.add_argument("expression")
    eval_parser.add_argument("--await-promise", action="store_true")

    call_parser = sub.add_parser("call", help="call an arbitrary CDP method without writing WebSocket plumbing")
    add_target_argument(call_parser)
    call_parser.add_argument("method", help="CDP method such as Runtime.evaluate or Network.enable")
    call_parser.add_argument("--params", default="{}", help="JSON object, or '-' to read JSON from stdin")
    call_parser.add_argument("--scope", choices=("page", "browser"), default="page")

    network_parser = sub.add_parser("network", help="capture request/response metadata around a click or navigation")
    add_target_argument(network_parser)
    network_parser.add_argument("mode",nargs="?",choices=("capture","wait-response","wait-request","wait-idle"),default="capture")
    network_parser.add_argument("--url-regex")
    network_parser.add_argument("--status",default="2xx")
    network_parser.add_argument("--idle-ms",type=float,default=500)
    trigger = network_parser.add_mutually_exclusive_group()
    trigger.add_argument("--click", metavar="SELECTOR", help="click this element after Network.enable")
    trigger.add_argument("--navigate", metavar="URL", help="navigate after Network.enable")
    network_parser.add_argument("--allow-submit", action="store_true", help="allow --click to use an HTML submit-like control")
    network_parser.add_argument("--duration", type=float, default=3.0, help="event collection duration after the trigger")
    network_parser.add_argument("--url-contains", help="return only requests/responses whose URL contains this text")
    network_parser.add_argument("--max-results", type=int, default=200, help="maximum summarized network records")

    click_parser = sub.add_parser("click", help="click a CSS-selected element through real CDP pointer events")
    add_target_argument(click_parser)
    click_parser.add_argument("selector")
    click_parser.add_argument(
        "--allow-submit",
        action="store_true",
        help="allow an HTML submit-like control; use only when the task's submit boundary has been explicitly authorized",
    )

    type_parser = sub.add_parser("type", help="replace text through a real pointer focus path and CDP text input")
    add_target_argument(type_parser)
    type_parser.add_argument("selector")
    type_parser.add_argument("value")

    fill_parser = sub.add_parser("fill", help="compatibility fallback: set a native input/textarea/select value through the DOM")
    add_target_argument(fill_parser)
    fill_parser.add_argument("selector")
    fill_parser.add_argument("value")

    upload_parser = sub.add_parser("upload", help="set one or more files on an input[type=file] through DOM.setFileInputFiles")
    add_target_argument(upload_parser)
    upload_parser.add_argument("selector")
    upload_parser.add_argument("files", nargs="+")
    upload_parser.add_argument("--check-only",action="store_true")
    upload_parser.add_argument("--max-file-bytes",type=int)
    upload_parser.add_argument("--max-total-bytes",type=int)

    wait_parser = sub.add_parser("wait", help="wait until a selector, text, URL fragment, or JavaScript expression becomes true")
    add_target_argument(wait_parser)
    condition = wait_parser.add_mutually_exclusive_group(required=True)
    condition.add_argument("--selector")
    condition.add_argument("--text")
    condition.add_argument("--url-contains")
    condition.add_argument("--expression")
    condition.add_argument("--dom-stable",metavar="SELECTOR")
    wait_parser.add_argument("--visible",action="store_true",help="selector must have a visible match")
    wait_parser.add_argument("--poll", type=float, default=0.25, help="poll interval in seconds")

    session_parser = sub.add_parser("session", help="one locked page WebSocket; stdin/stdout JSONL requests")
    add_target_argument(session_parser)

    new_parser=sub.add_parser("wait-new",help="wait for elements absent from an identity baseline")
    transition_parser=sub.add_parser("wait-transition",help="observe text states until a predicate completes")
    mutation_parser=sub.add_parser("wait-mutation",help="wait for a scoped DOM mutation and optional expression")
    elements_parser=sub.add_parser("elements",help="read bounded element identities for a wait baseline")
    for observer in (new_parser,transition_parser,mutation_parser,elements_parser):
        add_target_argument(observer)
        observer.add_argument("--selector",required=observer in (new_parser,transition_parser,elements_parser))
        observer.add_argument("--within")
        observer.add_argument("--attribute",action="append",dest="attributes")
        observer.add_argument("--identity-attribute",help="semantic DOM identity, such as id or data-message-id")
    new_parser.add_argument("--baseline",help="JSON array of identities captured before the action")
    transition_parser.add_argument("--initial-text")
    transition_parser.add_argument("--intermediate-text",action="append",default=[])
    transition_parser.add_argument("--until-expression",required=True,help="completion expression with observed and value in scope")
    mutation_parser.add_argument("--until-expression")
    for waiting in (wait_parser,new_parser,transition_parser,mutation_parser):
        if waiting is not wait_parser: waiting.add_argument("--poll",type=float,default=0.1)
        waiting.add_argument("--stable-ms",type=float,default=500)
        waiting.add_argument("--click",help="trigger click after installing observer and baseline")
        waiting.add_argument("--click-within")
        waiting.add_argument("--allow-submit",action="store_true")
    wait_parser.add_argument("--attribute",action="append",dest="attributes")
    artifact_parser=sub.add_parser("resolve-artifact",help="resolve an element's resource URL and filename")
    fetch_parser=sub.add_parser("browser-fetch",help="bounded fetch in the authorized page, saved to OS temp")
    add_target_argument(artifact_parser)
    artifact_parser.add_argument("selector")
    artifact_parser.add_argument("--within")
    add_target_argument(fetch_parser)
    fetch_parser.add_argument("url")
    fetch_parser.add_argument("--max-bytes",type=int,default=20*1024*1024)
    fetch_parser.add_argument("--evidence-on-error",action="store_true")
    screenshot_parser=sub.add_parser("screenshot",help="capture a page or selected element as PNG")
    snapshot_parser=sub.add_parser("snapshot",help="return bounded HTML and geometry without credential attributes")
    for diagnostic in (screenshot_parser,snapshot_parser):
        add_target_argument(diagnostic)
        diagnostic.add_argument("--selector",required=diagnostic is snapshot_parser)
        diagnostic.add_argument("--within")
    screenshot_parser.add_argument("--output",required=True)
    snapshot_parser.add_argument("--max-chars",type=int,default=10000)
    for risky in (click_parser,type_parser,fill_parser,upload_parser,wait_parser,new_parser,transition_parser,mutation_parser,network_parser,eval_parser,call_parser,session_parser):
        risky.add_argument("--evidence-on-error",action="store_true")
    for scoped in (click_parser,type_parser,fill_parser,upload_parser,inspect_parser,text_parser,wait_parser,network_parser):
        scoped.add_argument("--within", help="unique ancestor selector")
    for guarded in (click_parser,type_parser,fill_parser,upload_parser,screenshot_parser,snapshot_parser,artifact_parser):
        guarded.add_argument("--expect-text", help="exact normalized visible text")
        guarded.add_argument("--expect-role", help="ARIA or native role")
        guarded.add_argument("--expect-count", type=int, default=1)
        guarded.add_argument("--allow-multiple", action="store_true", help="explicitly use first of expected matches")
        guarded.add_argument("--predicate", help="JavaScript predicate with el in scope")
    type_parser.add_argument("--verify", choices=("exact","contains","none"),default="exact")
    return parser


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    return browser_status(args.browser, timeout=args.timeout)


def command_tabs(args: argparse.Namespace) -> dict[str, Any]:
    pages = page_targets(ensure_then_targets(args.browser, timeout=args.timeout))
    return {"count": len(pages), "pages": [target_view(item) for item in pages]}


def command_open(args: argparse.Namespace) -> dict[str, Any]:
    ensure_browser(args.browser, timeout=args.timeout)
    version = require_browser(args.endpoint, timeout=args.timeout)
    with browser_client(version, timeout=args.timeout) as client:
        result = client.call("Target.createTarget", {"url": args.url})
    target_id = str(result.get("targetId", ""))
    targets = list_targets(args.endpoint, timeout=args.timeout)
    target = next((item for item in page_targets(targets) if item.get("id") == target_id), None)
    return {"opened": True, "target": target_view(target) if target else {"id": target_id, "title": "", "url": args.url}}


def command_focus(args: argparse.Namespace) -> dict[str, Any]:
    target=selected_target(args.browser,args.target,timeout=args.timeout)
    with locked_page(args,target) as page:
        page.call("Page.bringToFront")
    return {"focused":True,"target":target_view(target)}


def command_navigate(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.browser, args.target, timeout=args.timeout)
    if any(getattr(args,key,None) for key in ("expected_url","expected_origin","expected_title_regex")):
        TargetLock(str(target["id"]),args.expected_url or str(target["url"]),args.expected_origin,args.expected_title_regex).validate(target)
    with page_client(target, timeout=args.timeout) as client:
        if args.expected_url:
            actual=client.evaluate("location.href")
            if actual!=args.expected_url:
                raise BrowserCdpError("Page changed before explicit navigation",code="TARGET_LOCK_VIOLATION",context={"expected_url":args.expected_url,"actual_url":actual})
        client.call("Page.enable")
        nav = client.call("Page.navigate", {"url": args.url})
        ready = wait_ready(client, timeout=args.timeout)
        href = client.evaluate("location.href")
        title = client.evaluate("document.title")
    return {"navigated": True, "targetId": target["id"], "readyState": ready, "title": title, "href": href, "navigation": nav}


def command_eval_like(args: argparse.Namespace, expression: str, *, await_promise: bool = False) -> dict[str, Any]:
    target = selected_target(args.browser, args.target, timeout=args.timeout)
    with locked_page(args, target) as client:
        value = client.evaluate(expression, await_promise=await_promise)
    return {"target": target_view(target), "value": value}


def command_text(args: argparse.Namespace) -> dict[str, Any]:
    limit = max(0, int(args.limit))
    expression = f"(() => {{ const t = document.body?.innerText || ''; return {{text:t.slice(0,{limit}), length:t.length, truncated:t.length>{limit}}}; }})()"
    return command_eval_like(args, scope_expression(expression,args.within))


def command_inspect(args: argparse.Namespace) -> dict[str, Any]:
    return command_eval_like(
        args,
        scope_expression(inspect_expression(max(0, int(args.text_limit)), all_controls=args.all_controls),args.within),
    )


def command_call(args: argparse.Namespace) -> dict[str, Any]:
    params = read_json_object(args.params)
    if args.scope == "browser":
        ensure_browser(args.browser, timeout=args.timeout)
        version = require_browser(args.endpoint, timeout=args.timeout)
        with browser_client(version, timeout=args.timeout) as client:
            result = client.call(args.method, params)
        return {"scope": "browser", "method": args.method, "result": result}
    target = selected_target(args.browser, args.target, timeout=args.timeout)
    with locked_page(args, target) as client:
        result = client.call(args.method, params)
    return {"scope": "page", "target": target_view(target), "method": args.method, "result": result}


def command_network(args: argparse.Namespace) -> dict[str, Any]:
    target=selected_target(args.browser,args.target,timeout=args.timeout)
    with locked_page(args,target) as page:
        result=observe_network(page,vars(args))
    return {"target":target_view(target),**result}


def command_click(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.browser, args.target, timeout=args.timeout)
    with locked_page(args, target) as page:
        result = pointer_click(page,args.selector,SelectorGuard.from_options(vars(args)),allow_submit=args.allow_submit)
    return {"target":target_view(target),**result}


def command_type(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.browser, args.target, timeout=args.timeout)
    with locked_page(args, target) as page:
        result = type_text(page,args.selector,args.value,SelectorGuard.from_options(vars(args)),verify=args.verify)
    return {"target":target_view(target),**result}


def command_fill(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.browser,args.target,timeout=args.timeout)
    with locked_page(args,target) as page:
        result = fill_native(page,args.selector,args.value,SelectorGuard.from_options(vars(args)))
    return {"target":target_view(target),**result}


def command_upload(args: argparse.Namespace) -> dict[str, Any]:
    target=selected_target(args.browser,args.target,timeout=args.timeout)
    with locked_page(args,target) as page:
        result=upload_files(page,args.selector,args.files,SelectorGuard.from_options(vars(args)),check_only=args.check_only,max_file_bytes=args.max_file_bytes,max_total_bytes=args.max_total_bytes)
    return {"target":target_view(target),**result}


def command_wait(args: argparse.Namespace) -> dict[str, Any]:
    target=selected_target(args.browser,args.target,timeout=args.timeout)
    kind={"wait-new":"new","wait-transition":"transition","wait-mutation":"mutation"}.get(args.command,"stable" if getattr(args,"dom_stable",None) else "condition")
    options=vars(args).copy()
    if getattr(args,"baseline",None):
        options["baseline"]=json.loads(args.baseline)
    if getattr(args,"dom_stable",None):
        options["selector"]=args.dom_stable
    with locked_page(args,target) as page:
        result=wait_condition(page,kind,options)
    return {"target":target_view(target),**result}


def dispatch(args: argparse.Namespace) -> Any:
    if args.command in {"resolve-artifact","browser-fetch"}:
        target=selected_target(args.browser,args.target,timeout=args.timeout)
        with locked_page(args,target) as page:
            result=resolve_artifact(page,args.selector,SelectorGuard.from_options(vars(args))) if args.command=="resolve-artifact" else browser_fetch(page,args.url,max_bytes=args.max_bytes,timeout=args.timeout)
        return {"target":target_view(target),**result}
    if args.command in {"screenshot","snapshot"}:
        from browser_runtime.evidence import screenshot, snapshot
        target=selected_target(args.browser,args.target,timeout=args.timeout)
        with locked_page(args,target) as page:
            if args.command=="screenshot":result=screenshot(page,args.output,args.selector,SelectorGuard.from_options(vars(args)))
            else:result=snapshot(page,args.selector,SelectorGuard.from_options(vars(args)),max_chars=args.max_chars)
        return {"target":target_view(target),**result}
    if args.command == "profiles":
        if any(option is not None for option in (args.profile, args.endpoint, args.user_data_dir, args.profile_directory)):
            raise BrowserCdpError("profiles only accepts --config and output options")
        return {"configFile": str(args.config), "profiles": [
            {"name": config.identity, "endpoint": config.endpoint,
             "userDataDir": config.user_data_dir, "profileDirectory": config.profile_directory}
            for config in (BrowserConfig(), *(profile.config for profile in load_profiles(args.config)))
        ]}
    if args.command == "profile-save":
        if args.profile is not None or args.endpoint is None or args.user_data_dir is None:
            raise BrowserCdpError("profile-save requires explicit --endpoint and --user-data-dir and does not accept --profile")
        profile = save_profile(args.name, args.browser, args.config)
        return {"saved": True, "name": profile.name, "configFile": str(args.config)}
    if args.command == "status":
        return command_status(args)
    if args.command == "ensure":
        return ensure_browser(args.browser, timeout=args.timeout)
    if args.command == "tabs":
        return command_tabs(args)
    if args.command == "open":
        return command_open(args)
    if args.command == "focus":
        return command_focus(args)
    if args.command == "navigate":
        return command_navigate(args)
    if args.command == "title":
        return command_eval_like(args, "document.title")
    if args.command == "text":
        return command_text(args)
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "eval":
        return command_eval_like(args, read_expression(args.expression), await_promise=args.await_promise)
    if args.command == "call":
        return command_call(args)
    if args.command == "network":
        return command_network(args)
    if args.command == "click":
        return command_click(args)
    if args.command == "type":
        return command_type(args)
    if args.command == "fill":
        return command_fill(args)
    if args.command == "upload":
        return command_upload(args)
    if args.command in {"wait","wait-new","wait-transition","wait-mutation"}:
        return command_wait(args)
    if args.command == "elements":
        return command_eval_like(args,observation_expression(args.selector,args.within,args.attributes,args.identity_attribute))
    raise BrowserCdpError(f"Unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    try:
        args = parser.parse_args()
        args.timeout = validate_timeout(args.timeout)
        if args.command != "profiles":
            args.browser = resolve_profile(args.profile, args.config, args.endpoint, args.user_data_dir, args.profile_directory)
            args.endpoint = args.browser.endpoint
        if args.command == "session":
            target = selected_target(args.browser, args.target, timeout=args.timeout)
            with locked_page(args, target) as page:
                serve_session(page, sys.stdin, sys.stdout, evidence_on_error=args.evidence_on_error)
            return 0
        emit(dispatch(args), compact=args.compact)
    except BrowserCdpError as exc:
        emit(exc.as_dict(), compact="--compact" in sys.argv)
        return 2
    except (OSError, ValueError, re.error) as exc:
        emit(BrowserCdpError(str(exc), code="IO_ERROR" if isinstance(exc, OSError) else "INVALID_ARGUMENT").as_dict(), compact="--compact" in sys.argv)
        return 2
    except Exception as exc:
        emit(BrowserCdpError(str(exc),code="INTERNAL_ERROR").as_dict(),compact="--compact" in sys.argv)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
