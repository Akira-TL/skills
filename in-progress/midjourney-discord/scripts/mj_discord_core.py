#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


READ_ONLY_COMMANDS = {"info", "help", "settings"}
READ_ONLY_COMPLETION_MARKERS = {
    "info": ("Your info -",),
    "help": ("GETTING STARTED?",),
    "settings": ("Adjust your settings here.",),
}
SUPPORTED_ACTIONS = {
    "U1", "U2", "U3", "U4",
    "V1", "V2", "V3", "V4",
    "Reroll",
    "Upscale (Subtle)",
    "Upscale (Creative)",
    "Vary (Subtle)",
    "Vary (Strong)",
    "Zoom Out 2x",
    "Zoom Out 1.5x",
    "Animate (High motion)",
    "Animate (Low motion)",
}
REMIX_CAPABLE_ACTIONS = {
    "V1", "V2", "V3", "V4",
    "Vary (Subtle)", "Vary (Strong)",
}
COMPOSER_SELECTOR = '[role="textbox"][aria-label]'


class MjDiscordError(RuntimeError):
    pass


def emit(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def normalize_url(value: str) -> str:
    return value.split("?", 1)[0].rstrip("/")


def browser_cli_candidates() -> list[Path]:
    candidates: list[Path] = []
    env = os.environ.get("BROWSER_ACCESS_CLI")
    if env:
        candidates.append(Path(env).expanduser())

    home = Path.home()
    candidates.extend([
        home / ".agents/skills/browser-access/scripts/browser_cdp.py",
        home / ".codex/skills/browser-access/scripts/browser_cdp.py",
    ])

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.extend([
            parent / "browser-access/scripts/browser_cdp.py",
            parent / "productivity/browser-access/scripts/browser_cdp.py",
        ])

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_browser_cli() -> Path:
    for candidate in browser_cli_candidates():
        if candidate.is_file():
            return candidate
    searched = "\n".join(f"- {p}" for p in browser_cli_candidates())
    raise MjDiscordError(
        "browser-access CLI not found. Install browser-access or set "
        f"BROWSER_ACCESS_CLI. Searched:\n{searched}"
    )


def run_browser(args: argparse.Namespace, *parts: str) -> dict:
    cli = resolve_browser_cli()
    uv = shutil.which("uv")
    if not uv:
        raise MjDiscordError("uv is required to run browser-access browser_cdp.py")

    command = [uv, "run", str(cli), "--compact"]
    if args.endpoint:
        command += ["--endpoint", args.endpoint]
    command += list(parts)

    proc = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=max(args.timeout + 10, 25),
    )
    if proc.returncode != 0:
        raise MjDiscordError(
            f"browser-access failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()}"
        )

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise MjDiscordError(f"browser-access returned no JSON: {proc.stdout!r}")


def eval_js(args: argparse.Namespace, target: str, expression: str) -> object:
    result = run_browser(args, "eval", "--target", target, expression)
    return result.get("value")


def list_tabs(args: argparse.Namespace) -> list[dict]:
    result = run_browser(args, "tabs")
    return list(result.get("pages") or [])


def resolve_target(args: argparse.Namespace) -> dict:
    expected = normalize_url(args.channel_url)
    matches = [
        page for page in list_tabs(args)
        if page.get("type", "page") == "page"
        and normalize_url(str(page.get("url", ""))) == expected
    ]
    if len(matches) != 1:
        raise MjDiscordError(
            f"Expected exactly one already-open Discord tab for {expected}; "
            f"found {len(matches)}. No navigation was attempted."
        )

    target = matches[0]
    current = eval_js(
        args,
        target["id"],
        "({href:location.href,title:document.title,"
        "composer:document.querySelector('[role=\"textbox\"][aria-label]')?.getAttribute('aria-label')||null})",
    )
    if not isinstance(current, dict):
        raise MjDiscordError("Unable to inspect the locked Discord tab")
    if normalize_url(str(current.get("href", ""))) != expected:
        raise MjDiscordError("Discord tab changed URL after target resolution; aborting")
    if not current.get("composer"):
        raise MjDiscordError("Discord message composer is not available in the locked tab")

    target = dict(target)
    target["composer"] = current.get("composer")
    target["title"] = current.get("title") or target.get("title")
    return target


MESSAGE_SNAPSHOT_JS = r"""
Array.from(document.querySelectorAll('li[id^="chat-messages-"]')).slice(-80).map(e => ({
  id: e.id,
  text: e.innerText || '',
  buttons: Array.from(e.querySelectorAll('button')).map(b => {
    const text = (b.innerText || '').trim();
    const emoji = b.querySelector('img[alt]')?.getAttribute('alt') || '';
    return text || emoji;
  }).filter(Boolean),
  original_urls: Array.from(e.querySelectorAll('a.originalLink[href], a[data-role="img"][href]'))
    .map(a => a.href),
  image_urls: Array.from(e.querySelectorAll('img'))
    .filter(img => img.alt === '图片' || img.alt === 'Image')
    .map(img => img.currentSrc || img.src)
    .filter(Boolean),
  job_urls: Array.from(e.querySelectorAll('a[href*="midjourney.com/jobs/"]')).map(a => a.href)
}))
"""


def message_snapshots(args: argparse.Namespace, target: str) -> list[dict]:
    value = eval_js(args, target, MESSAGE_SNAPSHOT_JS)
    if not isinstance(value, list):
        return []
    return [m for m in value if isinstance(m, dict)]


def message_ids(args: argparse.Namespace, target: str) -> set[str]:
    return {m.get("id") for m in message_snapshots(args, target) if m.get("id")}


def parse_job_status(text: str) -> tuple[str, int | None]:
    if "Waiting to start" in text:
        return "waiting", None
    match = re.search(r"\((\d{1,3})%\)", text)
    if match:
        return "running", int(match.group(1))
    if "Open on website for full quality" in text:
        return "completed", 100
    if " - Upscaled (" in text:
        return "completed", 100
    lowered = text.lower()
    if "failed" in lowered or "error" in lowered:
        return "error", None
    return "unknown", None


def enrich_message(message: dict) -> dict:
    out = dict(message)
    status, progress = parse_job_status(str(message.get("text", "")))
    out["status"] = status
    out["progress"] = progress
    urls = list(dict.fromkeys(message.get("job_urls") or []))
    out["job_url"] = urls[0] if urls else None
    out["original_urls"] = list(dict.fromkeys(message.get("original_urls") or []))
    out["image_urls"] = list(dict.fromkeys(message.get("image_urls") or []))
    return out


def find_message(
    messages: list[dict],
    *,
    message_id: str | None = None,
    contains: str | None = None,
    require_button: str | None = None,
) -> dict | None:
    for message in reversed(messages):
        if message_id and message.get("id") != message_id:
            continue
        text = str(message.get("text", ""))
        if contains and contains not in text:
            continue
        if require_button and require_button not in (message.get("buttons") or []):
            continue
        return message
    return None


def select_unique_message(
    messages: list[dict],
    *,
    message_id: str | None = None,
    contains: str | None = None,
    require_button: str | None = None,
) -> dict | None:
    if message_id:
        return find_message(
            messages,
            message_id=message_id,
            require_button=require_button,
        )

    if not contains:
        raise MjDiscordError("Message selection requires message_id or contains")

    candidates = [
        message for message in messages
        if contains in str(message.get("text", ""))
        and (
            not require_button
            or require_button in (message.get("buttons") or [])
        )
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise MjDiscordError(
            f"--contains matched {len(candidates)} Discord messages; "
            "use --message-id to avoid an ambiguous Midjourney action."
        )
    return candidates[0]


def wait_for_message(
    args: argparse.Namespace,
    target: str,
    *,
    baseline: set[str] | None = None,
    contains: str | None = None,
    message_id: str | None = None,
    require_button: str | None = None,
    completed: bool = False,
    text_markers: tuple[str, ...] | None = None,
) -> dict:
    deadline = time.monotonic() + args.timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        messages = message_snapshots(args, target)
        filtered = [
            m for m in messages
            if not baseline or m.get("id") not in baseline
        ]
        current = find_message(
            filtered,
            message_id=message_id,
            contains=contains,
            require_button=require_button,
        )
        if current:
            last = enrich_message(current)
            text = str(last.get("text", ""))
            if text_markers and not any(marker in text for marker in text_markers):
                time.sleep(args.poll)
                continue
            if not completed or last["status"] in {"completed", "error"}:
                return last
        time.sleep(args.poll)

    if last:
        last["timed_out"] = True
        return last
    raise MjDiscordError("Timed out waiting for a matching Midjourney Discord message")


def autocomplete_options(args: argparse.Namespace, target: str) -> list[dict]:
    expression = (
        "Array.from(document.querySelectorAll('[role=option]')).map(e=>"
        "({id:e.id,text:e.innerText||'',selected:e.getAttribute('aria-selected')}))"
    )
    value = eval_js(args, target, expression)
    return value if isinstance(value, list) else []


def type_into_composer(args: argparse.Namespace, target: str, value: str) -> None:
    run_browser(args, "type", "--target", target, COMPOSER_SELECTOR, value)


def choose_midjourney_command(
    args: argparse.Namespace,
    target: str,
    command_name: str,
) -> dict:
    wanted = f"/{command_name}"
    type_into_composer(args, target, wanted)
    time.sleep(0.2)

    options = autocomplete_options(args, target)
    matches = [
        option for option in options
        if wanted in str(option.get("text", "")).splitlines()[0]
        and "Midjourney Bot" in str(option.get("text", ""))
    ]
    if not matches:
        raise MjDiscordError(
            f"Midjourney Bot autocomplete option not found for {wanted}. "
            "The composer was not submitted."
        )
    option = matches[0]
    option_id = option.get("id")
    if not option_id:
        raise MjDiscordError(f"Autocomplete option for {wanted} has no DOM id")

    option_id_js = json.dumps(option_id, ensure_ascii=False)
    clicked = eval_js(
        args,
        target,
        f"""(() => {{
          const option = document.getElementById({option_id_js});
          if (!option) return {{ok:false,error:'autocomplete-option-missing'}};
          if (!((option.innerText || '').includes('Midjourney Bot'))) {{
            return {{ok:false,error:'autocomplete-provider-mismatch'}};
          }}
          option.click();
          return {{ok:true,id:option.id,text:option.innerText||'',interaction_mode:'dom-click'}};
        }})()""",
    )
    if not isinstance(clicked, dict) or not clicked.get("ok"):
        raise MjDiscordError(f"Unable to select Midjourney autocomplete option: {clicked}")

    time.sleep(0.25)
    structured = eval_js(
        args,
        target,
        """(() => {
          const composer = document.querySelector('[role="textbox"][aria-label]');
          if (!composer) return null;
          return {
            text: composer.innerText || '',
            command_name: composer.querySelector('[class*="commandName"]')?.innerText || null,
            has_inline_option: !!composer.querySelector('[data-slate-inline="true"]')
          };
        })()""",
    )
    if not isinstance(structured, dict) or structured.get("command_name") != wanted:
        raise MjDiscordError(
            f"Discord did not convert {wanted} into a structured slash command; "
            "the command was not submitted."
        )
    option = dict(option)
    option["selection"] = clicked
    option["composer"] = structured
    return option


def dispatch_enter(args: argparse.Namespace, target: str) -> None:
    payload = json.dumps(
        {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
        ensure_ascii=False,
    )
    run_browser(
        args,
        "call",
        "--target",
        target,
        "Input.dispatchKeyEvent",
        "--params",
        payload,
    )
    payload = json.dumps(
        {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
        ensure_ascii=False,
    )
    run_browser(
        args,
        "call",
        "--target",
        target,
        "Input.dispatchKeyEvent",
        "--params",
        payload,
    )


def insert_text(args: argparse.Namespace, target: str, value: str) -> None:
    payload = json.dumps({"text": value}, ensure_ascii=False)
    run_browser(
        args,
        "call",
        "--target",
        target,
        "Input.insertText",
        "--params",
        payload,
    )


def doctor(args: argparse.Namespace) -> dict:
    target = resolve_target(args)
    dialogs = remix_dialogs(args, target["id"])
    return {
        "ok": True,
        "channel_url": normalize_url(args.channel_url),
        "target_id": target["id"],
        "title": target.get("title"),
        "composer": target.get("composer"),
        "browser_access_cli": str(resolve_browser_cli()),
        "navigation_performed": False,
        "visible_remix_dialog": dialogs[0] if len(dialogs) == 1 else None,
        "visible_remix_dialogs": dialogs,
    }


def invoke_read_only(args: argparse.Namespace) -> dict:
    command = args.command_name.lstrip("/")
    if command not in READ_ONLY_COMMANDS:
        raise MjDiscordError(
            f"Unsupported read-only command: {command}. "
            f"Allowed: {', '.join(sorted(READ_ONLY_COMMANDS))}"
        )

    target = resolve_target(args)
    baseline = message_ids(args, target["id"])
    choose_midjourney_command(args, target["id"], command)
    dispatch_enter(args, target["id"])

    message = wait_for_message(
        args,
        target["id"],
        baseline=baseline,
        text_markers=READ_ONLY_COMPLETION_MARKERS[command],
    )
    return {
        "ok": True,
        "command": f"/{command}",
        "message": message,
    }


def imagine(args: argparse.Namespace) -> dict:
    prompt = args.prompt.strip()
    if not prompt:
        raise MjDiscordError("Prompt must not be empty")

    target = resolve_target(args)
    baseline = message_ids(args, target["id"])
    selected = choose_midjourney_command(args, target["id"], "imagine")
    if not selected.get("composer", {}).get("has_inline_option"):
        raise MjDiscordError(
            "Discord /imagine did not expose the prompt argument slot; not submitted"
        )
    insert_text(args, target["id"], prompt)

    composer = eval_js(
        args,
        target["id"],
        "document.querySelector('[role=\"textbox\"][aria-label]')?.innerText||''",
    )
    if prompt not in str(composer):
        raise MjDiscordError("Prompt did not reach the Discord /imagine composer; not submitted")

    dispatch_enter(args, target["id"])

    marker = prompt[: min(120, len(prompt))]
    message = wait_for_message(
        args,
        target["id"],
        baseline=baseline,
        contains=marker,
        completed=not args.no_wait,
    )
    return {
        "ok": True,
        "submitted_prompt": prompt,
        "message": message,
    }


def recent(args: argparse.Namespace) -> dict:
    target = resolve_target(args)
    messages = [
        enrich_message(m)
        for m in message_snapshots(args, target["id"])
        if "Midjourney Bot" in str(m.get("text", ""))
    ]
    return {
        "ok": True,
        "count": min(args.limit, len(messages)),
        "messages": messages[-args.limit :],
    }


def canonical_action_label(value: str) -> str:
    if value.lower() in {"reroll", "refresh", "🔄"}:
        return "Reroll"
    return value


def extract_prompt(text: str) -> str | None:
    """Extract the most recent rendered Midjourney prompt from a Discord message group."""
    separators = (
        " - @",
        " - Image #",
        " - Variations",
        " - Remix (",
        " - Upscaled (",
        " - Zoom Out",
        " - Make Square",
    )
    for raw_line in reversed(text.splitlines()):
        line = raw_line.strip()
        if len(line) < 8:
            continue
        if line in {"Midjourney Bot", "已验证 APP"}:
            continue
        if "http://" in line or "https://" in line:
            continue
        if any(token in line for token in separators):
            for separator in separators:
                if separator in line:
                    line = line.split(separator, 1)[0].rstrip()
                    break
            if len(line) >= 8:
                return line
    return None


def prompt_signature(text: str, *, limit: int = 96) -> str | None:
    """Extract a stable prompt prefix from a Midjourney message."""
    prompt = extract_prompt(text)
    return prompt[:limit] if prompt else None


def stabilize_message(args: argparse.Namespace, target: str, message_id: str) -> None:
    js_id = json.dumps(message_id, ensure_ascii=False)
    value = eval_js(
        args,
        target,
        f"""(() => {{
          const message = document.getElementById({js_id});
          if (!message) return false;
          message.scrollIntoView({{block:'center', inline:'nearest'}});
          return true;
        }})()""",
    )
    if value is not True:
        raise MjDiscordError("Source message is no longer present in the Discord DOM")
    time.sleep(0.35)


def remix_dialogs(args: argparse.Namespace, target: str) -> list[dict]:
    value = eval_js(
        args,
        target,
        """(() => {
          const visible = e => {
            const r = e.getBoundingClientRect();
            const s = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
          };
          const pointerReachable = el => {
            if (!el || !visible(el)) return false;
            const r = el.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return !!hit && (hit === el || el.contains(hit));
          };
          return Array.from(document.querySelectorAll('[role=dialog], [aria-modal=true]'))
            .filter(e => visible(e) && (e.innerText || '').includes('Remix Prompt'))
            .map((dialog, index) => {
              const textarea = dialog.querySelector('textarea');
              const buttons = Array.from(dialog.querySelectorAll('button'));
              const submit = buttons.find(b => ['提交','Submit'].includes((b.innerText || '').trim()));
              const cancel = buttons.find(b => ['取消','Cancel'].includes((b.innerText || '').trim()));
              return {
                index,
                title: (dialog.innerText || '').split('\\n')[0] || 'Remix Prompt',
                prompt: textarea?.value || '',
                textarea_id: textarea?.id || '',
                has_submit: !!submit,
                has_cancel: !!cancel,
                textarea_pointer_reachable: pointerReachable(textarea),
                submit_pointer_reachable: pointerReachable(submit),
                cancel_pointer_reachable: pointerReachable(cancel)
              };
            });
        })()""",
    )
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def select_remix_dialog(
    dialogs: list[dict],
    *,
    expected_prompt: str | None = None,
    contains: str | None = None,
) -> dict | None:
    candidates = list(dialogs)
    if expected_prompt is not None:
        expected = expected_prompt.strip()
        candidates = [
            dialog for dialog in candidates
            if str(dialog.get("prompt", "")).strip() == expected
        ]
    if contains is not None:
        candidates = [
            dialog for dialog in candidates
            if contains in str(dialog.get("prompt", ""))
        ]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise MjDiscordError(
            f"Multiple Remix Prompt dialogs match the selector ({len(candidates)}); "
            "refusing an ambiguous dialog action."
        )
    return candidates[0]


