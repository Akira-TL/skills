#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mj_discord_core import *  # noqa: F403
from mj_discord_media import collect_related, download_all, imagine_with_images, upload_images


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

    upload_parser = sub.add_parser("upload", help="Upload reference images to the locked Discord channel.")
    upload_parser.add_argument("files", nargs="+", help="Local image paths to upload in one Discord message.")

    imagine_parser = sub.add_parser("imagine", help="Submit /imagine, optionally with uploaded reference images.")
    imagine_parser.add_argument("prompt")
    imagine_parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Local reference image path. Repeat for multiple images.",
    )
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

    collect_parser = sub.add_parser(
        "collect",
        help="Collect all visible Midjourney image results related to one root job.",
    )
    locate = collect_parser.add_mutually_exclusive_group(required=True)
    locate.add_argument("--message-id")
    locate.add_argument("--contains")

    download_parser = sub.add_parser("download", help="Download the original Discord attachment.")
    locate = download_parser.add_mutually_exclusive_group(required=True)
    locate.add_argument("--message-id")
    locate.add_argument("--contains")
    download_parser.add_argument("--output", required=True)

    download_all_parser = sub.add_parser(
        "download-all",
        help="Download all visible image attachments related to one root Midjourney job.",
    )
    locate = download_all_parser.add_mutually_exclusive_group(required=True)
    locate.add_argument("--message-id")
    locate.add_argument("--contains")
    download_all_parser.add_argument("--output", required=True, help="Output directory.")

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
        elif args.subcommand == "upload":
            result = upload_images(args)
        elif args.subcommand == "imagine":
            result = imagine_with_images(args) if args.image else imagine(args)
        elif args.subcommand == "recent":
            result = recent(args)
        elif args.subcommand == "action":
            result = action(args)
        elif args.subcommand == "remix":
            result = remix_command(args)
        elif args.subcommand == "collect":
            result = collect_related(args)
        elif args.subcommand == "download":
            result = download(args)
        elif args.subcommand == "download-all":
            result = download_all(args)
        else:
            raise AssertionError(args.subcommand)
        emit(result)
        return 0
    except (MjDiscordError, subprocess.TimeoutExpired, OSError) as exc:
        emit({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
