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


def submit_remix_dialog(
    args: argparse.Namespace,
    target: str,
    *,
    prompt: str | None,
    expected_prompt: str | None = None,
    dialog_contains: str | None = None,
) -> dict:
    dialogs = remix_dialogs(args, target)
    if not dialogs:
        raise MjDiscordError("No visible Midjourney Remix Prompt dialog is available")
    if expected_prompt is None and dialog_contains is None and len(dialogs) != 1:
        raise MjDiscordError(
            f"{len(dialogs)} visible Remix Prompt dialogs are open; "
            "refusing to guess which one to submit."
        )
    dialog = select_remix_dialog(
        dialogs,
        expected_prompt=expected_prompt,
        contains=dialog_contains,
    )
    if not dialog:
        raise MjDiscordError("No visible Remix Prompt dialog matches the requested prompt")
    textarea_id = str(dialog.get("textarea_id") or "")
    if not textarea_id:
        raise MjDiscordError("Selected Remix Prompt has no identifiable textarea")

    if prompt is not None:
        if not dialog.get("textarea_pointer_reachable"):
            raise MjDiscordError(
                "Selected Remix Prompt textarea is not pointer-reachable, likely because "
                "another dialog is stacked above it; refusing to edit the wrong prompt."
            )
        selector = f'[id={json.dumps(textarea_id, ensure_ascii=False)}]'
        run_browser(args, "type", "--target", target, selector, prompt)

    if not dialog.get("submit_pointer_reachable"):
        raise MjDiscordError(
            "Selected Remix Prompt submit button is not pointer-reachable, likely because "
            "another dialog is stacked above it; refusing to submit."
        )

    textarea_id_js = json.dumps(textarea_id, ensure_ascii=False)
    prepared = eval_js(
        args,
        target,
        f"""(() => {{
          document.querySelectorAll('[data-mj-discord-cli-modal-submit]').forEach(
            e => e.removeAttribute('data-mj-discord-cli-modal-submit')
          );
          const textarea = document.getElementById({textarea_id_js});
          if (!textarea) return {{ok:false,error:'textarea-not-found'}};
          const dialog = textarea.closest('[role=dialog], [aria-modal=true]');
          if (!dialog) return {{ok:false,error:'dialog-not-found'}};
          const button = Array.from(dialog.querySelectorAll('button')).find(
            b => ['提交','Submit'].includes((b.innerText || '').trim())
          );
          if (!button) return {{ok:false,error:'submit-not-found'}};
          button.setAttribute('data-mj-discord-cli-modal-submit','1');
          return {{ok:true,prompt:textarea.value || '',textarea_id:textarea.id || ''}};
        }})()""",
    )
    if not isinstance(prepared, dict) or not prepared.get("ok"):
        raise MjDiscordError(f"Unable to prepare Remix submit button: {prepared}")
    if prompt is not None and prepared.get("prompt") != prompt:
        raise MjDiscordError(
            "Discord Remix textarea did not retain the requested replacement prompt; "
            "refusing to submit."
        )

    click_result = run_browser(
        args,
        "click",
        "--target",
        target,
        '[data-mj-discord-cli-modal-submit="1"]',
    )
    return {
        "dialog": dialog,
        "submitted": prepared,
        "click_result": click_result,
    }

def trigger_action_button(
    args: argparse.Namespace,
    target: str,
    message_id: str,
    label: str,
) -> dict:
    """Trigger an exact Midjourney component with a real pointer click.

    Discord reuses component DOM aggressively. Live testing showed that calling
    HTMLElement.click() on a visually correct V button can invoke stale React state
    from another Midjourney message. Therefore message buttons are scoped to the
    exact message-accessories container and must be activated through browser-access'
    pointer click path.
    """
    snowflake = message_id.rsplit("-", 1)[-1]
    accessory_id = f"message-accessories-{snowflake}"
    js_label = json.dumps(label, ensure_ascii=False)
    js_accessory = json.dumps(accessory_id, ensure_ascii=False)
    expression = f"""
(() => {{
  document.querySelectorAll('[data-mj-discord-cli-target]').forEach(
    e => e.removeAttribute('data-mj-discord-cli-target')
  );
  const accessories = document.getElementById({js_accessory});
  if (!accessories) return {{ok:false,error:'message-accessories-not-found'}};
  const wanted = {js_label};
  const buttons = Array.from(accessories.querySelectorAll('button'));
  const labels = buttons.map(b => {{
    const text = (b.innerText || '').trim();
    const emoji = b.querySelector('img[alt]')?.getAttribute('alt') || '';
    return text || (emoji === '🔄' ? 'Reroll' : emoji);
  }});
  const index = labels.findIndex(x => x === wanted);
  if (index < 0) return {{ok:false,error:'button-not-found',labels}};
  const button = buttons[index];
  if (button.disabled || button.getAttribute('aria-disabled') === 'true') {{
    return {{ok:false,error:'button-disabled',label:wanted,index,labels}};
  }}
  button.scrollIntoView({{block:'center',inline:'nearest'}});
  button.setAttribute('data-mj-discord-cli-target','1');
  const rect = button.getBoundingClientRect();
  return {{ok:true,label:wanted,index,labels,accessory_id:{js_accessory},
    rect:{{x:rect.x,y:rect.y,width:rect.width,height:rect.height}},
    interaction_mode:'pointer'}};
}})()
"""
    prepared = eval_js(args, target, expression)
    if not isinstance(prepared, dict) or not prepared.get("ok"):
        raise MjDiscordError(f"Unable to prepare action button: {prepared}")

    time.sleep(0.6)
    try:
        clicked = run_browser(
            args,
            "click",
            "--target",
            target,
            '[data-mj-discord-cli-target="1"]',
        )
    finally:
        try:
            eval_js(
                args,
                target,
                "document.querySelectorAll('[data-mj-discord-cli-target]').forEach("
                "e=>e.removeAttribute('data-mj-discord-cli-target')); true",
            )
        except Exception:
            pass

    prepared["click_result"] = clicked
    return prepared


def action(args: argparse.Namespace) -> dict:
    label = canonical_action_label(args.button)
    if label not in SUPPORTED_ACTIONS:
        raise MjDiscordError(
            f"Unsupported/non-modal action {label!r}. "
            "Modal actions such as Vary (Region) and Custom Zoom require dedicated interaction."
        )

    target = resolve_target(args)
    preexisting_dialogs = remix_dialogs(args, target["id"])
    if preexisting_dialogs:
        raise MjDiscordError(
            f"{len(preexisting_dialogs)} Remix Prompt dialog(s) were already open before this action. "
            "Refusing to click a different Midjourney component. "
            "Use the remix subcommand to inspect them first."
        )
    messages = message_snapshots(args, target["id"])
    message = select_unique_message(
        messages,
        message_id=args.message_id,
        contains=args.contains,
        require_button=("🔄" if label == "Reroll" else label),
    )
    if not message:
        raise MjDiscordError("No unique eligible message matched the requested action")

    baseline = {m.get("id") for m in messages if m.get("id")}
    source_prompt = extract_prompt(str(message.get("text", "")))
    source_marker = source_prompt[:96] if source_prompt else None
    if not source_marker:
        raise MjDiscordError(
            "Unable to derive a stable prompt signature from the source message; "
            "refusing an uncorrelated action."
        )
    stabilize_message(args, target["id"], message["id"])
    raced_dialogs = remix_dialogs(args, target["id"])
    if raced_dialogs:
        raise MjDiscordError(
            f"{len(raced_dialogs)} Remix Prompt dialog(s) appeared while preparing this action. "
            "Refusing to click because their ownership cannot be proven safely. "
            "Use the remix subcommand to inspect them first."
        )
    prepared = trigger_action_button(args, target["id"], message["id"], label)
    click_result = {
        "clicked": True,
        "interaction_mode": prepared.get("interaction_mode"),
        "message_id": message["id"],
        "label": label,
        "browser_click": prepared.get("click_result"),
    }

    remix_dialog = None
    if label in REMIX_CAPABLE_ACTIONS:
        probe_deadline = time.monotonic() + min(6.0, args.timeout)
        while time.monotonic() < probe_deadline:
            current_dialogs = remix_dialogs(args, target["id"])
            if len(current_dialogs) > 1:
                raise MjDiscordError(
                    "Multiple Remix Prompt dialogs appeared while handling this action; "
                    "refusing to guess which one belongs to the current job."
                )
            if current_dialogs:
                remix_dialog = select_remix_dialog(
                    current_dialogs,
                    expected_prompt=source_prompt,
                )
                if not remix_dialog:
                    raise MjDiscordError(
                        "A Remix Prompt dialog appeared, but its prompt does not match "
                        "the source Midjourney job; refusing cross-task interaction."
                    )
                break
            new_messages = [
                m for m in message_snapshots(args, target["id"])
                if m.get("id") not in baseline
            ]
            if find_message(new_messages, contains=source_marker):
                break
            time.sleep(min(0.35, args.poll))

    remix_submission = None
    if remix_dialog:
        dialog_prompt = str(remix_dialog.get("prompt") or "")
        if source_marker not in dialog_prompt:
            # Exact message-button clicks should never open a Remix prompt for a
            # different source job. Close the mismatched dialog before failing so
            # the browser remains usable for the next command.
            eval_js(
                args,
                target["id"],
                """(() => {
                  const d = Array.from(document.querySelectorAll('[role=dialog],[aria-modal=true]'))
                    .find(e => (e.innerText || '').includes('Remix Prompt'));
                  const b = d && Array.from(d.querySelectorAll('button')).find(
                    x => ['取消','Cancel'].includes((x.innerText || '').trim())
                  );
                  if (b) b.click();
                  return !!b;
                })()""",
            )
            raise MjDiscordError(
                "Remix dialog prompt did not match the source message; "
                "the dialog was cancelled and no variation was submitted."
            )
        if not args.accept_remix and args.remix_prompt is None:
            return {
                "ok": True,
                "clicked": prepared,
                "click_result": click_result,
                "source_message": enrich_message(message),
                "correlation_marker": source_marker,
                "modal_required": True,
                "remix_dialog": remix_dialog,
            }
        remix_submission = submit_remix_dialog(
            args,
            target["id"],
            prompt=args.remix_prompt,
            expected_prompt=source_prompt,
        )

    if args.no_wait:
        return {
            "ok": True,
            "clicked": prepared,
            "click_result": click_result,
            "source_message": enrich_message(message),
            "correlation_marker": (
                args.remix_prompt[:96] if args.remix_prompt else source_marker
            ),
            "remix_dialog": remix_dialog,
            "remix_submission": remix_submission,
        }

    correlation_marker = (
        args.remix_prompt[:96]
        if args.remix_prompt
        else source_marker
    )
    result = wait_for_message(
        args,
        target["id"],
        baseline=baseline,
        contains=correlation_marker,
        completed=True,
    )
    return {
        "ok": True,
        "clicked": prepared,
        "click_result": click_result,
        "source_message": enrich_message(message),
        "remix_dialog": remix_dialog,
        "remix_submission": remix_submission,
        "correlation_marker": correlation_marker,
        "result_message": result,
    }


def prepare_dialog_button(
    args: argparse.Namespace,
    target: str,
    dialog: dict,
    labels: tuple[str, ...],
    marker: str,
) -> dict:
    textarea_id = str(dialog.get("textarea_id") or "")
    if not textarea_id:
        raise MjDiscordError("Selected Remix Prompt has no identifiable textarea")
    textarea_id_js = json.dumps(textarea_id, ensure_ascii=False)
    labels_js = json.dumps(list(labels), ensure_ascii=False)
    marker_js = json.dumps(marker, ensure_ascii=False)
    value = eval_js(
        args,
        target,
        f"""(() => {{
          document.querySelectorAll('[data-mj-discord-cli-dialog-action]').forEach(
            e => e.removeAttribute('data-mj-discord-cli-dialog-action')
          );
          const textarea = document.getElementById({textarea_id_js});
          if (!textarea) return {{ok:false,error:'textarea-not-found'}};
          const dialog = textarea.closest('[role=dialog], [aria-modal=true]');
          if (!dialog) return {{ok:false,error:'dialog-not-found'}};
          const wanted = {labels_js};
          const button = Array.from(dialog.querySelectorAll('button')).find(
            b => wanted.includes((b.innerText || '').trim())
          );
          if (!button) return {{ok:false,error:'button-not-found',labels:wanted}};
          button.setAttribute('data-mj-discord-cli-dialog-action', {marker_js});
          return {{ok:true,text:(button.innerText||'').trim(),textarea_id:textarea.id||''}};
        }})()""",
    )
    if not isinstance(value, dict) or not value.get("ok"):
        raise MjDiscordError(f"Unable to prepare Remix dialog action: {value}")
    return value


def remix_command(args: argparse.Namespace) -> dict:
    target = resolve_target(args)
    dialogs = remix_dialogs(args, target["id"])

    if args.remix_action == "inspect":
        return {
            "ok": True,
            "visible": bool(dialogs),
            "count": len(dialogs),
            "remix_dialogs": dialogs,
        }

    if not dialogs:
        raise MjDiscordError("No visible Midjourney Remix Prompt dialog is available")

    dialog = select_remix_dialog(dialogs, contains=args.dialog_contains)
    if not dialog:
        raise MjDiscordError("No visible Remix Prompt dialog matches --dialog-contains")

    if args.remix_action == "cancel":
        prepared = prepare_dialog_button(
            args,
            target["id"],
            dialog,
            ("取消", "Cancel"),
            "cancel",
        )
        textarea_id_js = json.dumps(str(dialog.get("textarea_id") or ""), ensure_ascii=False)
        clicked = eval_js(
            args,
            target["id"],
            f"""(() => {{
              const textarea = document.getElementById({textarea_id_js});
              if (!textarea) return {{ok:false,error:'textarea-not-found'}};
              const dialog = textarea.closest('[role=dialog], [aria-modal=true]');
              if (!dialog) return {{ok:false,error:'dialog-not-found'}};
              const button = Array.from(dialog.querySelectorAll('button')).find(
                b => ['取消','Cancel'].includes((b.innerText || '').trim())
              );
              if (!button) return {{ok:false,error:'cancel-not-found'}};
              button.click();
              return {{ok:true,interaction_mode:'validated-dom-click'}};
            }})()""",
        )
        if not isinstance(clicked, dict) or not clicked.get("ok"):
            raise MjDiscordError(f"Unable to cancel selected Remix dialog: {clicked}")
        time.sleep(0.2)
        remaining = remix_dialogs(args, target["id"])
        return {
            "ok": True,
            "cancelled": True,
            "dialog": dialog,
            "prepared": prepared,
            "click_result": clicked,
            "visible_after_count": len(remaining),
        }

    if args.remix_action != "submit":
        raise AssertionError(args.remix_action)

    baseline = message_ids(args, target["id"])
    source_prompt = str(dialog.get("prompt") or "")
    submission = submit_remix_dialog(
        args,
        target["id"],
        prompt=args.prompt,
        expected_prompt=source_prompt,
    )
    effective_prompt = args.prompt if args.prompt is not None else source_prompt
    marker = effective_prompt[:96] if effective_prompt else None

    if args.no_wait:
        return {
            "ok": True,
            "remix_submission": submission,
            "correlation_marker": marker,
        }

    result = wait_for_message(
        args,
        target["id"],
        baseline=baseline,
        contains=marker,
        completed=True,
    )
    return {
        "ok": True,
        "remix_submission": submission,
        "correlation_marker": marker,
        "result_message": result,
    }

def select_message_for_download(args: argparse.Namespace, target: str) -> dict:
    messages = message_snapshots(args, target)
    message = select_unique_message(
        messages,
        message_id=args.message_id,
        contains=args.contains,
    )
    if not message:
        raise MjDiscordError("No matching Discord message found for download")
    enriched = enrich_message(message)
    if not enriched["original_urls"]:
        raise MjDiscordError("Matching message has no original Discord attachment URL")
    return enriched


def default_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name or "midjourney-result.webp"


def download(args: argparse.Namespace) -> dict:
    target = resolve_target(args)
    message = select_message_for_download(args, target["id"])
    url = message["original_urls"][0]

    output = Path(args.output).expanduser()
    if output.exists() and output.is_dir():
        output = output / default_filename(url)
    elif str(args.output).endswith(("/", os.sep)):
        output.mkdir(parents=True, exist_ok=True)
        output = output / default_filename(url)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type")

    output.write_bytes(data)
    return {
        "ok": True,
        "message_id": message.get("id"),
        "source_url": url,
        "output": str(output.resolve()),
        "bytes": len(data),
        "content_type": content_type,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate Midjourney Bot through an already-open, user-authorized Discord tab."
    )
    parser.add_argument(
        "--channel-url",
        default=os.environ.get("MJ_DISCORD_CHANNEL_URL"),
        help="Exact authorized Discord channel URL (or MJ_DISCORD_CHANNEL_URL).",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("BROWSER_CDP_ENDPOINT"),
        help="Optional browser-access CDP endpoint.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("MJ_DISCORD_TIMEOUT", "180")),
        help="Operation timeout in seconds (default: 180).",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=float(os.environ.get("MJ_DISCORD_POLL", "1.5")),
        help="Polling interval in seconds (default: 1.5).",
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("doctor", help="Verify exact-tab lock and composer availability.")

    command_parser = sub.add_parser("command", help="Run a read-only Midjourney slash command.")
    command_parser.add_argument("command_name", choices=sorted(READ_ONLY_COMMANDS))

    imagine_parser = sub.add_parser("imagine", help="Submit /imagine.")
    imagine_parser.add_argument("prompt")
    imagine_parser.add_argument("--no-wait", action="store_true")

    recent_parser = sub.add_parser("recent", help="Return recent Midjourney messages.")
    recent_parser.add_argument("--limit", type=int, default=10)

    action_parser = sub.add_parser("action", help="Click one supported non-modal action button.")
    locate = action_parser.add_mutually_exclusive_group(required=True)
    locate.add_argument("--message-id")
    locate.add_argument("--contains")
    action_parser.add_argument("--button", required=True)
    action_parser.add_argument(
        "--accept-remix",
        action="store_true",
        help="If Remix Mode opens a prompt dialog, submit the existing prompt unchanged.",
    )
    action_parser.add_argument(
        "--remix-prompt",
        help="If Remix Mode opens a prompt dialog, replace it with this prompt and submit.",
    )
    action_parser.add_argument("--no-wait", action="store_true")

    remix_parser = sub.add_parser("remix", help="Inspect or resolve an already-open Remix Prompt dialog.")
    remix_parser.add_argument(
        "--dialog-contains",
        help="Select the visible Remix Prompt whose prompt contains this text.",
    )
    remix_sub = remix_parser.add_subparsers(dest="remix_action", required=True)
    remix_sub.add_parser("inspect")
    remix_submit = remix_sub.add_parser("submit")
    remix_submit.add_argument("--prompt")
    remix_submit.add_argument("--no-wait", action="store_true")
    remix_sub.add_parser("cancel")

    download_parser = sub.add_parser("download", help="Download the original Discord attachment.")
    locate = download_parser.add_mutually_exclusive_group(required=True)
    locate.add_argument("--message-id")
    locate.add_argument("--contains")
    download_parser.add_argument("--output", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.channel_url:
        parser.error("--channel-url or MJ_DISCORD_CHANNEL_URL is required")
    if not normalize_url(args.channel_url).startswith("https://discord.com/channels/"):
        parser.error("--channel-url must be a Discord channel URL")
    if args.timeout <= 0 or args.poll <= 0:
        parser.error("--timeout and --poll must be positive")

    try:
        if args.subcommand == "doctor":
            result = doctor(args)
        elif args.subcommand == "command":
            result = invoke_read_only(args)
        elif args.subcommand == "imagine":
            result = imagine(args)
        elif args.subcommand == "recent":
            result = recent(args)
        elif args.subcommand == "action":
            result = action(args)
        elif args.subcommand == "remix":
            result = remix_command(args)
        elif args.subcommand == "download":
            result = download(args)
        else:
            raise AssertionError(args.subcommand)
        emit(result)
        return 0
    except (MjDiscordError, subprocess.TimeoutExpired, OSError) as exc:
        emit({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
