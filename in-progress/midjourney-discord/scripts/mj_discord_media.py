#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from mj_discord_core import (
    COMPOSER_SELECTOR,
    MjDiscordError,
    choose_midjourney_command,
    dispatch_enter,
    enrich_message,
    eval_js,
    insert_text,
    message_ids,
    message_snapshots,
    prompt_signature,
    resolve_target,
    run_browser,
    select_unique_message,
    wait_for_message,
)

SUPPORTED_IMAGE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif",
}


def _url_filename(url: str) -> str:
    return Path(unquote(urlparse(url).path)).name


def validate_image_paths(paths: list[str]) -> list[Path]:
    if not paths:
        raise MjDiscordError("At least one image path is required")
    resolved: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise MjDiscordError(f"Reference image does not exist: {path}")
        if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise MjDiscordError(
                f"Unsupported reference image type {path.suffix!r}: {path}. "
                f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_SUFFIXES))}"
            )
        resolved.append(path)
    return resolved


def composer_attachment_state(args: argparse.Namespace, target: str) -> dict:
    value = eval_js(
        args,
        target,
        r"""(() => {
          const composer = document.querySelector('[role="textbox"][aria-label]');
          const clean = s => (s || '').replace(/﻿/g, '').trim();
          const bodyTail = document.body.innerText.slice(-5000);
          const blobImages = Array.from(document.querySelectorAll('img[src^="blob:"]'))
            .filter(img => {
              const r = img.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            });
          const removeButtons = Array.from(document.querySelectorAll('button')).filter(b => {
            const text = (b.innerText || '').trim();
            const aria = (b.getAttribute('aria-label') || '').trim();
            return ['移除附件','Remove attachment'].includes(text) ||
              ['移除附件','Remove attachment'].includes(aria);
          });
          const inputs = Array.from(document.querySelectorAll('input[type=file]')).map((e, i) => ({
            i,
            multiple: !!e.multiple,
            accept: e.accept || '',
            disabled: !!e.disabled
          }));
          return {
            composer_text: clean(composer?.innerText || ''),
            body_tail: bodyTail,
            blob_count: blobImages.length,
            remove_button_count: removeButtons.length,
            file_inputs: inputs
          };
        })()""",
    )
    if not isinstance(value, dict):
        raise MjDiscordError("Unable to inspect Discord composer attachment state")
    return value


def _assert_clean_composer(args: argparse.Namespace, target: str) -> dict:
    state = composer_attachment_state(args, target)
    if state.get("composer_text"):
        raise MjDiscordError(
            "Discord composer already contains unsent text; refusing to overwrite the user's draft."
        )
    if int(state.get("blob_count") or 0) or int(state.get("remove_button_count") or 0):
        raise MjDiscordError(
            "Discord composer already contains pending attachments; refusing to mix uploads."
        )
    inputs = list(state.get("file_inputs") or [])
    usable = [i for i in inputs if not i.get("disabled")]
    if len(usable) != 1:
        raise MjDiscordError(
            f"Expected exactly one usable Discord file input; found {len(usable)}"
        )
    return state


def _wait_for_attachment_preview(
    args: argparse.Namespace,
    target: str,
    files: list[Path],
) -> dict:
    expected = [p.name for p in files]
    deadline = time.monotonic() + args.timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        state = composer_attachment_state(args, target)
        last = state
        tail = str(state.get("body_tail") or "")
        filenames_visible = all(name in tail for name in expected)
        enough_controls = int(state.get("remove_button_count") or 0) >= len(files)
        enough_blobs = int(state.get("blob_count") or 0) >= len(files)
        if filenames_visible and (enough_controls or enough_blobs):
            return state
        time.sleep(args.poll)
    raise MjDiscordError(
        "Timed out waiting for Discord attachment preview. "
        f"Expected files={expected}, last_state={last}"
    )


def _message_contains_uploaded_files(message: dict, names: list[str]) -> bool:
    urls = list(message.get("original_urls") or [])
    found = {_url_filename(url) for url in urls}
    return all(name in found for name in names)


def _wait_for_uploaded_message(
    args: argparse.Namespace,
    target: str,
    baseline: set[str],
    files: list[Path],
) -> dict:
    names = [p.name for p in files]
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        for message in message_snapshots(args, target):
            if message.get("id") in baseline:
                continue
            text = str(message.get("text") or "")
            if "Midjourney Bot" in text:
                continue
            if _message_contains_uploaded_files(message, names):
                return enrich_message(message)
        time.sleep(args.poll)
    raise MjDiscordError(
        "Timed out waiting for the Discord upload message to expose attachment URLs"
    )


def upload_images(
    args: argparse.Namespace,
    *,
    target: dict | None = None,
    files: list[str] | None = None,
) -> dict:
    paths = validate_image_paths(files if files is not None else list(args.files))
    target = target or resolve_target(args)
    target_id = target["id"]

    before = _assert_clean_composer(args, target_id)
    baseline = message_ids(args, target_id)

    run_browser(
        args,
        "upload",
        "--target",
        target_id,
        "input[type=file]",
        *[str(path) for path in paths],
    )
    preview = _wait_for_attachment_preview(args, target_id, paths)

    run_browser(args, "click", "--target", target_id, COMPOSER_SELECTOR)
    dispatch_enter(args, target_id)

    message = _wait_for_uploaded_message(args, target_id, baseline, paths)
    urls = list(message.get("original_urls") or [])
    by_name = {_url_filename(url): url for url in urls}
    missing = [path.name for path in paths if path.name not in by_name]
    if missing:
        raise MjDiscordError(
            f"Discord upload message was created but attachment URLs are missing: {missing}"
        )

    return {
        "ok": True,
        "files": [str(path) for path in paths],
        "before": {
            "composer_text": before.get("composer_text"),
            "pending_attachments": before.get("remove_button_count"),
        },
        "preview": {
            "blob_count": preview.get("blob_count"),
            "remove_button_count": preview.get("remove_button_count"),
        },
        "message": message,
        "reference_urls": [by_name[path.name] for path in paths],
    }


def imagine_with_images(args: argparse.Namespace) -> dict:
    prompt = args.prompt.strip()
    if not prompt:
        raise MjDiscordError("Prompt must not be empty")
    target = resolve_target(args)

    upload = upload_images(args, target=target, files=list(args.image or []))
    reference_urls = list(upload["reference_urls"])
    effective_prompt = " ".join([*reference_urls, prompt])

    baseline = message_ids(args, target["id"])
    selected = choose_midjourney_command(args, target["id"], "imagine")
    if not selected.get("composer", {}).get("has_inline_option"):
        raise MjDiscordError(
            "Discord /imagine did not expose the prompt argument slot; not submitted"
        )

    insert_text(args, target["id"], effective_prompt)
    composer = eval_js(
        args,
        target["id"],
        "document.querySelector('[role=\"textbox\"][aria-label]')?.innerText||''",
    )
    if prompt not in str(composer) or not all(url in str(composer) for url in reference_urls):
        raise MjDiscordError(
            "Reference URLs and prompt did not reach the Discord /imagine composer; not submitted"
        )

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
        "effective_prompt": effective_prompt,
        "reference_upload": upload,
        "message": message,
    }


def classify_midjourney_message(message: dict) -> str:
    text = str(message.get("text") or "")
    buttons = set(message.get("buttons") or [])
    if " - Upscaled (" in text:
        return "upscale"
    if " - Remix (" in text or " - Variations" in text:
        return "variation_grid"
    if " - Image #" in text:
        return "selected_image"
    if "Zoom Out" in text:
        return "zoom"
    if {"U1", "U2", "U3", "U4"}.issubset(buttons):
        return "grid"
    if message.get("original_urls"):
        return "image_result"
    return "message"


def collect_related(
    args: argparse.Namespace,
    *,
    target: dict | None = None,
) -> dict:
    target = target or resolve_target(args)
    messages = message_snapshots(args, target["id"])

    root = select_unique_message(
        messages,
        message_id=getattr(args, "message_id", None),
        contains=getattr(args, "contains", None),
    )
    if not root or "Midjourney Bot" not in str(root.get("text") or ""):
        raise MjDiscordError("No unique matching root Midjourney message found")

    signature = prompt_signature(str(root.get("text") or ""))
    if not signature:
        raise MjDiscordError(
            "Unable to derive a stable prompt signature from the root Midjourney message"
        )

    related: list[dict] = []
    seen_ids: set[str] = set()
    for message in messages:
        message_id = str(message.get("id") or "")
        if not message_id or message_id in seen_ids:
            continue
        text = str(message.get("text") or "")
        if signature not in text:
            continue
        if "Midjourney Bot" not in text:
            continue
        enriched = enrich_message(message)
        enriched["result_type"] = classify_midjourney_message(enriched)
        related.append(enriched)
        seen_ids.add(message_id)

    attachments: list[dict] = []
    seen_urls: set[str] = set()
    for message in related:
        for index, url in enumerate(message.get("original_urls") or []):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            attachments.append({
                "url": url,
                "filename": _url_filename(url),
                "message_id": message.get("id"),
                "result_type": message.get("result_type"),
                "index": index,
            })

    return {
        "ok": True,
        "root_message": enrich_message(root),
        "prompt_signature": signature,
        "message_count": len(related),
        "attachment_count": len(attachments),
        "messages": related,
        "attachments": attachments,
    }


def _download_url(url: str, output: Path, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {
        "output": str(output.resolve()),
        "bytes": len(data),
        "content_type": content_type,
    }


def download_all(args: argparse.Namespace) -> dict:
    collected = collect_related(args)
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[dict] = []
    used_names: set[str] = set()
    for position, item in enumerate(collected["attachments"], start=1):
        original_name = item["filename"] or f"midjourney-{position}.bin"
        name = original_name
        if name in used_names or (output_dir / name).exists():
            suffix = Path(original_name).suffix
            stem = Path(original_name).stem
            short_id = str(item.get("message_id") or "message").rsplit("-", 1)[-1][-8:]
            name = f"{stem}-{short_id}-{position}{suffix}"
        used_names.add(name)

        result = _download_url(item["url"], output_dir / name, args.timeout)
        downloaded.append({**item, **result})

    return {
        "ok": True,
        "prompt_signature": collected["prompt_signature"],
        "output_dir": str(output_dir),
        "downloaded_count": len(downloaded),
        "downloaded": downloaded,
    }
