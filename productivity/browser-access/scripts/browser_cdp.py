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
import time
from typing import Any

from browser_cdp_core import (
    DEFAULT_ENDPOINT,
    PROFILE_IDENTITY,
    BrowserCdpError,
    CdpProtocolError,
    browser_client,
    chrome_file_path,
    dispatch_primary_click,
    emit,
    ensure_browser,
    ensure_then_targets,
    fill_expression,
    inspect_expression,
    interaction_point_expression,
    list_targets,
    page_client,
    page_targets,
    probe_version,
    read_expression,
    read_json_object,
    require_browser,
    selected_target,
    replace_focused_text,
    summarize_network_events,
    target_state_expression,
    target_view,
    wait_ready,
)

def add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        help="page target: exact ID, unique ID prefix, unique title fragment, or unique URL fragment",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fast deterministic control surface for browser-access's WSL -> Windows Chrome CDP adapter"
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"CDP HTTP endpoint (default: {DEFAULT_ENDPOINT})")
    parser.add_argument("--timeout", type=float, default=15.0, help="operation timeout in seconds (default: 15)")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="probe the CDP endpoint without launching Chrome")
    sub.add_parser("ensure", help="reuse the persistent Agent Chrome or launch it with the agent-browser Profile")
    sub.add_parser("tabs", help="list page targets only")

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

    wait_parser = sub.add_parser("wait", help="wait until a selector, text, URL fragment, or JavaScript expression becomes true")
    add_target_argument(wait_parser)
    condition = wait_parser.add_mutually_exclusive_group(required=True)
    condition.add_argument("--selector")
    condition.add_argument("--text")
    condition.add_argument("--url-contains")
    condition.add_argument("--expression")
    wait_parser.add_argument("--poll", type=float, default=0.25, help="poll interval in seconds")

    return parser


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    version = probe_version(args.endpoint, timeout=min(args.timeout, 2.0))
    return {
        "connected": version is not None,
        "endpoint": args.endpoint,
        "profileIdentity": PROFILE_IDENTITY,
        "browser": version.get("Browser") if version else None,
        "protocolVersion": version.get("Protocol-Version") if version else None,
    }


def command_tabs(args: argparse.Namespace) -> dict[str, Any]:
    pages = page_targets(ensure_then_targets(args.endpoint, timeout=args.timeout))
    return {"count": len(pages), "pages": [target_view(item) for item in pages]}


def command_open(args: argparse.Namespace) -> dict[str, Any]:
    ensure_browser(args.endpoint, timeout=args.timeout)
    version = require_browser(args.endpoint, timeout=args.timeout)
    with browser_client(version, timeout=args.timeout) as client:
        result = client.call("Target.createTarget", {"url": args.url})
    target_id = str(result.get("targetId", ""))
    targets = list_targets(args.endpoint, timeout=args.timeout)
    target = next((item for item in page_targets(targets) if item.get("id") == target_id), None)
    return {"opened": True, "target": target_view(target) if target else {"id": target_id, "title": "", "url": args.url}}


def command_focus(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    version = require_browser(args.endpoint, timeout=args.timeout)
    with browser_client(version, timeout=args.timeout) as client:
        client.call("Target.activateTarget", {"targetId": target["id"]})
    return {"focused": True, "target": target_view(target)}


def command_navigate(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    with page_client(target, timeout=args.timeout) as client:
        client.call("Page.enable")
        nav = client.call("Page.navigate", {"url": args.url})
        ready = wait_ready(client, timeout=args.timeout)
        href = client.evaluate("location.href")
        title = client.evaluate("document.title")
    return {"navigated": True, "targetId": target["id"], "readyState": ready, "title": title, "href": href, "navigation": nav}


def command_eval_like(args: argparse.Namespace, expression: str, *, await_promise: bool = False) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    with page_client(target, timeout=args.timeout) as client:
        value = client.evaluate(expression, await_promise=await_promise)
    return {"target": target_view(target), "value": value}


def command_text(args: argparse.Namespace) -> dict[str, Any]:
    limit = max(0, int(args.limit))
    expression = f"(() => {{ const t = document.body?.innerText || ''; return {{text:t.slice(0,{limit}), length:t.length, truncated:t.length>{limit}}}; }})()"
    return command_eval_like(args, expression)


def command_inspect(args: argparse.Namespace) -> dict[str, Any]:
    return command_eval_like(
        args,
        inspect_expression(max(0, int(args.text_limit)), all_controls=args.all_controls),
    )


def command_call(args: argparse.Namespace) -> dict[str, Any]:
    params = read_json_object(args.params)
    if args.scope == "browser":
        ensure_browser(args.endpoint, timeout=args.timeout)
        version = require_browser(args.endpoint, timeout=args.timeout)
        with browser_client(version, timeout=args.timeout) as client:
            result = client.call(args.method, params)
        return {"scope": "browser", "method": args.method, "result": result}
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    with page_client(target, timeout=args.timeout) as client:
        result = client.call(args.method, params)
    return {"scope": "page", "target": target_view(target), "method": args.method, "result": result}


def command_network(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    trigger_result: Any = None
    with page_client(target, timeout=args.timeout) as client:
        client.call("Network.enable")
        if args.click:
            trigger_result = client.evaluate(
                interaction_point_expression(args.click, allow_submit=args.allow_submit)
            )
            if not isinstance(trigger_result, dict):
                raise CdpProtocolError("Pointer target inspection did not return an object")
            dispatch_primary_click(client, trigger_result)
        elif args.navigate:
            client.call("Page.enable")
            trigger_result = client.call("Page.navigate", {"url": args.navigate})
        events = client.collect_events(max(0.0, args.duration))
    records = summarize_network_events(events, url_contains=args.url_contains)
    max_results = max(0, int(args.max_results))
    return {
        "target": target_view(target),
        "trigger": trigger_result,
        "eventCount": len(events),
        "recordCount": len(records),
        "returnedRecordCount": min(len(records), max_results),
        "records": records[:max_results],
    }


def command_click(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    with page_client(target, timeout=args.timeout) as client:
        point = client.evaluate(
            interaction_point_expression(args.selector, allow_submit=args.allow_submit)
        )
        if not isinstance(point, dict):
            raise CdpProtocolError("Pointer target inspection did not return an object")
        dispatch_primary_click(client, point)
    return {"clicked": True, "target": target_view(target), "interaction": point}


def command_type(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    with page_client(target, timeout=args.timeout) as client:
        point = client.evaluate(
            interaction_point_expression(args.selector, require_text_target=True)
        )
        if not isinstance(point, dict):
            raise CdpProtocolError("Text target inspection did not return an object")
        dispatch_primary_click(client, point)
        focused = client.evaluate(target_state_expression(args.selector))
        if not isinstance(focused, dict) or not focused.get("focused"):
            raise CdpProtocolError(
                "Pointer click did not focus the requested text target; refusing to send keyboard input"
            )
        replace_focused_text(client, args.value)
        state = client.evaluate(target_state_expression(args.selector))
    return {
        "typed": True,
        "target": target_view(target),
        "interaction": point,
        "state": state,
    }


def command_fill(args: argparse.Namespace) -> dict[str, Any]:
    return command_eval_like(args, fill_expression(args.selector, args.value))


def command_upload(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    files = [chrome_file_path(value) for value in args.files]
    with page_client(target, timeout=args.timeout) as client:
        client.call("DOM.enable")
        document = client.call("DOM.getDocument", {"depth": 1, "pierce": True})
        root = document.get("root", {})
        node_id = root.get("nodeId") if isinstance(root, dict) else None
        if not isinstance(node_id, int):
            raise CdpProtocolError("DOM.getDocument did not return a root nodeId")
        query = client.call("DOM.querySelector", {"nodeId": node_id, "selector": args.selector})
        file_node_id = query.get("nodeId")
        if not isinstance(file_node_id, int) or file_node_id == 0:
            raise CdpProtocolError(f"No element matches upload selector {args.selector!r}")
        client.call("DOM.setFileInputFiles", {"nodeId": file_node_id, "files": files})
        state = client.evaluate(
            f"(() => {{ const el=document.querySelector({json.dumps(args.selector, ensure_ascii=False)}); return el ? {{count:el.files?.length || 0, names:[...(el.files || [])].map(f=>f.name)}} : null; }})()"
        )
    return {"uploaded": True, "target": target_view(target), "files": files, "state": state}


def command_wait(args: argparse.Namespace) -> dict[str, Any]:
    target = selected_target(args.endpoint, args.target, timeout=args.timeout)
    if args.selector is not None:
        expression = f"!!document.querySelector({json.dumps(args.selector, ensure_ascii=False)})"
        condition = {"selector": args.selector}
    elif args.text is not None:
        expression = f"(document.body?.innerText || '').includes({json.dumps(args.text, ensure_ascii=False)})"
        condition = {"text": args.text}
    elif args.url_contains is not None:
        expression = f"location.href.includes({json.dumps(args.url_contains, ensure_ascii=False)})"
        condition = {"urlContains": args.url_contains}
    else:
        expression = args.expression
        condition = {"expression": args.expression}
    started = time.monotonic()
    deadline = started + args.timeout
    last: Any = None
    with page_client(target, timeout=args.timeout) as client:
        while time.monotonic() < deadline:
            last = client.evaluate(expression)
            if bool(last):
                return {
                    "met": True,
                    "elapsedSeconds": round(time.monotonic() - started, 3),
                    "condition": condition,
                    "target": target_view(target),
                    "value": last,
                }
            time.sleep(max(0.05, args.poll))
    raise BrowserCdpError(
        f"Condition was not met within {args.timeout:g}s: {json.dumps(condition, ensure_ascii=False)}; last value={last!r}"
    )


def dispatch(args: argparse.Namespace) -> Any:
    if args.command == "status":
        return command_status(args)
    if args.command == "ensure":
        return ensure_browser(args.endpoint, timeout=args.timeout)
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
    if args.command == "wait":
        return command_wait(args)
    raise BrowserCdpError(f"Unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        emit(dispatch(args), compact=args.compact)
    except BrowserCdpError as exc:
        emit({"ok": False, "error": str(exc)}, compact=args.compact)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
