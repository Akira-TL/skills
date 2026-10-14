#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["websocket-client>=1.8,<2"]
# ///
"""Agent 显式发起的单次完整读取或受保护续接；没有定时与语义判断。"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Protocol, cast

sys.dont_write_bytecode = True
from watch_controls import PROBE, conversation, object_fields, read_controls, verify_profile

VIEW = Path(__file__).with_name("reply-view.js").read_text(encoding="utf-8")


class Page(Protocol):
    def call(self, method: str, params: Mapping[str, object] | None = None, *, guard: str | None = None) -> object: ...
    def evaluate(self, expression: str, *, await_promise: bool = False) -> object: ...


@dataclass(frozen=True)
class Selectors:
    reply_selector: str
    user_selector: str
    model_selector: str
    ui_selector: str = ""
    payload_selector: str = ""
    payload_text: bool = False
    encoded_text: bool = False

    def expression(self) -> str:
        return f"(async () => {{ {VIEW}; return await replyView({json.dumps(asdict(self), ensure_ascii=False)}); }})()"


@dataclass
class Attempt:
    stage: str = "checking"
    insert_attempted: bool = False
    enter_attempted: bool = False
    confirmed: bool = False


def snapshot(page: Page, selectors: Selectors) -> Mapping[str, object]:
    return object_fields(page.evaluate(selectors.expression(), await_promise=True))


def read_window(view: Mapping[str, object], *, start: int = 0, limit: int = 6000,
                expected_version: str | None = None, payload_index: int | None = None) -> Mapping[str, object]:
    """版本锁定的分段输出；完整读取仍由 Agent 逐段完成。"""
    if start < 0 or limit < 1 or limit > 12000:
        raise ValueError("Read window requires nonnegative start and a limit from 1 to 12000")
    if (start > 0 or payload_index is not None) and expected_version is None:
        raise ValueError("Further segments and payload reads require the reviewed version")
    if expected_version is not None and view.get("version") != expected_version:
        raise ValueError("Reviewed page changed during segmented read")
    if payload_index is not None:
        payloads = view.get("payloads")
        if not isinstance(payloads, list) or not 0 <= payload_index < len(payloads):
            raise ValueError("Unknown payload index")
        payload = object_fields(payloads[payload_index])
        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("Payload text was not requested")
        facts: dict[str, object] = {"url": view.get("url"), "version": view.get("version"),
                                  "payload_index": payload_index, "sha": payload.get("sha")}
    else:
        text = view.get("text")
        if not isinstance(text, str):
            raise ValueError("Reply text is unavailable")
        facts = {key: value for key, value in view.items() if key not in {"text", "length", "point", "focused"}}
    if start > len(text):
        raise ValueError("Read offset exceeds the current text")
    end = min(start + limit, len(text))
    return {**facts, "text": text[start:end], "length": len(text), "text_start": start,
            "text_end": end, "text_complete": start == 0 and end == len(text),
            "next_start": end if end < len(text) else None}


def confirmation(page: Page, selectors: Selectors) -> Mapping[str, object]:
    # 提交后旧回复容器可被替换；只读用户消息与控件，不再绑定发送前回复。
    expression = f"(() => {{ {VIEW}; return {{...userView({json.dumps(asdict(selectors))}), controls: {PROBE}}}; }})()"
    return object_fields(page.evaluate(expression))


def non_pro(model: str) -> bool:
    return bool(model.strip()) and "pro" not in model.casefold()


def action_guard(selectors: Selectors, *, url: str, version: str, model: str,
                 draft: str, focused: bool, point: Mapping[str, object] | None = None) -> str:
    expected = json.dumps({"url": url, "version": version, "model": model, "draft": draft}, ensure_ascii=False)
    pointer = f"s.point!==null && s.point.x==={json.dumps(point['x'])} && s.point.y==={json.dumps(point['y'])}" if point else "s.point!==null"
    return f"""(async () => {{ {VIEW}; const s=await replyView({json.dumps(asdict(selectors))});
      const e={expected}; return s.url===e.url && s.version===e.version && s.model===e.model
        && !s.model.toLowerCase().includes('pro') && s.stop===0 && !s.connection_lost
        && s.dialogs===0 && s.attachments===0 && s.editor_count===1 && s.editable
        && s.draft===e.draft && {'s.focused' if focused else pointer}; }})()"""


def check_other_tabs(page: Page, *, url: str, target: str) -> None:
    """重复会话退让；不替 Agent 解决哪个标签页最新。"""
    result = object_fields(page.call("Target.getTargets"))
    targets = result.get("targetInfos")
    if not isinstance(targets, list):
        raise ValueError("Cannot verify duplicate tabs")
    for item in targets:
        facts = object_fields(item)
        if facts.get("type") != "page" or facts.get("targetId") == target:
            continue
        other_url = facts.get("url")
        if isinstance(other_url, str) and conversation(other_url) and conversation(other_url) == conversation(url):
            # 同会话重复目标应先由 Agent 消歧、处理全部输入现场，再重新发起。
            raise ValueError("Duplicate conversation tabs require Agent review")


def continue_once(page: Page, selectors: Selectors, *, url: str, target: str,
                  version: str, model: str, attempt: Attempt) -> Mapping[str, object]:
    if not re.fullmatch(r"[0-9a-f]{64}", version) or not non_pro(model):
        raise ValueError("A reviewed version and non-Pro model are required")
    before = snapshot(page, selectors)
    if before.get("url") != url or before.get("version") != version or before.get("model") != model:
        raise ValueError("Reviewed page changed")
    if type(before.get("user_count")) is not int or cast(int, before["user_count"]) < 1:
        raise ValueError("Verified user messages are required")
    attempt.stage = "focusing"
    page.call("Page.bringToFront", guard=action_guard(selectors, url=url, version=version,
                                                    model=model, draft="", focused=False))
    point = object_fields(snapshot(page, selectors).get("point"))
    guard = action_guard(selectors, url=url, version=version, model=model, draft="", focused=False, point=point)
    release_guard = f"location.href === {json.dumps(url)}"
    try:
        page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": point["x"], "y": point["y"],
                  "button": "left", "buttons": 1, "clickCount": 1}, guard=guard)
    finally:
        # 释放已尝试的按键不插入、提交或点击新的位置；仍守住文档锁。
        page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": point["x"], "y": point["y"],
                  "button": "left", "buttons": 0, "clickCount": 1}, guard=release_guard)
    check_other_tabs(page, url=url, target=target)
    attempt.stage = "inserting"
    # 请求结果不明也视作可能已插入；Agent 回读前不可重试。
    attempt.insert_attempted = True
    page.call("Input.insertText", {"text": "继续"},
              guard=action_guard(selectors, url=url, version=version, model=model, draft="", focused=True))
    attempt.stage = "sending"
    check_other_tabs(page, url=url, target=target)
    attempt.enter_attempted = True
    try:
        page.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter",
                  "windowsVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"},
                  guard=action_guard(selectors, url=url, version=version, model=model, draft="继续", focused=True))
    finally:
        page.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter",
                  "windowsVirtualKeyCode": 13}, guard=release_guard)
    attempt.stage = "confirming"
    after = confirmation(page, selectors)
    attempt.confirmed = (type(after.get("user_count")) is int
                         and cast(int, after["user_count"]) > cast(int, before["user_count"])
                         and after.get("latest_user") == "继续")
    attempt.stage = "confirmed" if attempt.confirmed else "unconfirmed"
    # 确认失败只返回事实，不再按键，不把空编辑器当发送成功。
    return {"attempt": asdict(attempt), "confirmation": {"before_user_count": before["user_count"],
            "after_user_count": after.get("user_count"), "latest_user_is_continue": after.get("latest_user") == "继续"},
            "controls": asdict(read_controls(after.get("controls")))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("read", "continue"))
    parser.add_argument("--browser-access-script", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--reply-selector", required=True)
    parser.add_argument("--user-selector", required=True)
    parser.add_argument("--model-selector", required=True)
    parser.add_argument("--ui-selector", default="")
    parser.add_argument("--payload-selector", default="")
    parser.add_argument("--payload-text", action="store_true")
    parser.add_argument("--encoded-text", action="store_true", help="已核验独立长 Base64 文本时，单列其长度与摘要")
    parser.add_argument("--text-start", type=int, default=0)
    parser.add_argument("--text-limit", type=int, default=6000, help="每段最多 12000 字符，默认 6000；返回 next_start")
    parser.add_argument("--payload-index", type=int, help="只返回指定载荷的一段全文，和 --text-start/--text-limit 配合")
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-model")
    args = parser.parse_args()
    attempt = Attempt()
    try:
        if not conversation(args.url):
            raise ValueError("An existing HTTPS ChatGPT conversation is required")
        script = args.browser_access_script.resolve(strict=True)
        verify_profile(script, args.endpoint)
        sys.path.insert(0, str(script.parent))
        session_type = importlib.import_module("browser_session").BrowserSession
        selectors = Selectors(args.reply_selector, args.user_selector, args.model_selector,
                              args.ui_selector, args.payload_selector,
                              args.payload_text or args.payload_index is not None, args.encoded_text)
        with session_type(args.endpoint, target=args.target, expected_url=args.url) as page:
            if args.operation == "read":
                result = read_window(snapshot(page, selectors), start=args.text_start, limit=args.text_limit,
                                     expected_version=args.expected_version, payload_index=args.payload_index)
            else:
                if not args.expected_version or not args.expected_model:
                    raise ValueError("Agent must supply its reviewed version and model")
                check_other_tabs(page, url=args.url, target=args.target)
                result = continue_once(page, selectors, url=args.url, target=args.target,
                                       version=args.expected_version, model=args.expected_model, attempt=attempt)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
        return 0
    except (KeyboardInterrupt, SystemExit):
        return 130
    except Exception as exc:
        code = getattr(exc, "code", "")
        print(json.dumps({"error_type": type(exc).__name__,
                          "error_code": code if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z_]+", code) else "",
                          "attempt": asdict(attempt)}, separators=(",", ":")), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
