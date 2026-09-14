#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "websocket-client>=1.8,<2",
# ]
# ///
"""Deterministic Chrome DevTools Protocol helper for browser-access.

This is the preferred control surface for the WSL -> Windows Chrome CDP adapter.
It centralizes Chrome lifecycle probing, target selection and common page actions so
agents do not need to recreate WebSocket/CDP plumbing for each browser task.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ENDPOINT = "http://localhost:9222"
PROFILE_IDENTITY = "agent-browser"
BLANK_URLS = {"", "about:blank", "chrome://newtab/", "chrome://new-tab-page/"}


class BrowserCdpError(RuntimeError):
    """Base error for deterministic browser/CDP failures."""


class TargetSelectionError(BrowserCdpError):
    """Raised when a page target cannot be selected unambiguously."""


class CdpProtocolError(BrowserCdpError):
    """Raised when Chrome returns a CDP protocol error or JavaScript exception."""


def emit(value: Any, *, compact: bool = False) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":") if compact else None,
            indent=None if compact else 2,
        )
    )


def http_json(endpoint: str, path: str, *, method: str = "GET", timeout: float = 5.0) -> Any:
    url = endpoint.rstrip("/") + path
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise BrowserCdpError(f"CDP HTTP request failed: {method} {url}: {exc}") from exc


def probe_version(endpoint: str, *, timeout: float = 1.5) -> dict[str, Any] | None:
    try:
        value = http_json(endpoint, "/json/version", timeout=timeout)
    except BrowserCdpError:
        return None
    return value if isinstance(value, dict) else None


def list_targets(endpoint: str, *, timeout: float = 5.0) -> list[dict[str, Any]]:
    value = http_json(endpoint, "/json/list", timeout=timeout)
    if not isinstance(value, list):
        raise BrowserCdpError("CDP /json/list did not return a target list")
    return [item for item in value if isinstance(item, dict)]


def page_targets(targets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in targets
        if item.get("type") == "page" and isinstance(item.get("webSocketDebuggerUrl"), str)
    ]


def target_view(target: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(target.get("id", "")),
        "title": str(target.get("title", "")),
        "url": str(target.get("url", "")),
    }


def _meaningful_page(target: dict[str, Any]) -> bool:
    return str(target.get("url", "")).strip() not in BLANK_URLS


def select_target(targets: Iterable[dict[str, Any]], selector: str | None) -> dict[str, Any]:
    pages = page_targets(targets)
    if not pages:
        raise TargetSelectionError("No page target is available in the Agent Chrome instance")

    if selector:
        needle = selector.casefold()
        exact = [item for item in pages if str(item.get("id", "")) == selector]
        if len(exact) == 1:
            return exact[0]
        matches = [
            item
            for item in pages
            if str(item.get("id", "")).casefold().startswith(needle)
            or needle in str(item.get("title", "")).casefold()
            or needle in str(item.get("url", "")).casefold()
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise TargetSelectionError(
                f"Target selector {selector!r} matched no page. Available pages: "
                + json.dumps([target_view(item) for item in pages], ensure_ascii=False)
            )
        raise TargetSelectionError(
            f"Target selector {selector!r} is ambiguous. Matches: "
            + json.dumps([target_view(item) for item in matches], ensure_ascii=False)
        )

    meaningful = [item for item in pages if _meaningful_page(item)]
    if len(meaningful) == 1:
        return meaningful[0]
    if len(pages) == 1:
        return pages[0]
    raise TargetSelectionError(
        "Multiple page targets are open; pass --target with an ID prefix, unique title fragment, "
        "or unique URL fragment. Available pages: "
        + json.dumps([target_view(item) for item in pages], ensure_ascii=False)
    )


@dataclass
class CdpClient:
    websocket_url: str
    timeout: float = 10.0

    def __post_init__(self) -> None:
        self._next_id = 1
        self._ws: Any | None = None
        self._events: list[dict[str, Any]] = []

    def __enter__(self) -> "CdpClient":
        try:
            import websocket  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - PEP 723 installs this for runtime use.
            raise BrowserCdpError(
                "websocket-client is unavailable; run this file through `uv run` so its inline dependency is installed"
            ) from exc
        try:
            self._ws = websocket.create_connection(
                self.websocket_url,
                timeout=self.timeout,
                suppress_origin=True,
            )
        except Exception as exc:
            raise BrowserCdpError(f"Cannot connect to CDP WebSocket {self.websocket_url}: {exc}") from exc
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._ws is None:
            raise BrowserCdpError("CDP WebSocket is not connected")
        message_id = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"id": message_id, "method": method}
        if params:
            payload["params"] = params
        self._ws.send(json.dumps(payload, ensure_ascii=False))
        while True:
            try:
                incoming = json.loads(self._ws.recv())
            except Exception as exc:
                raise BrowserCdpError(f"Failed while waiting for CDP response to {method}: {exc}") from exc
            if incoming.get("id") != message_id:
                if isinstance(incoming.get("method"), str):
                    self._events.append(incoming)
                continue
            if "error" in incoming:
                raise CdpProtocolError(f"{method} failed: {incoming['error']}")
            result = incoming.get("result", {})
            return result if isinstance(result, dict) else {"value": result}

    def collect_events(self, duration: float) -> list[dict[str, Any]]:
        if self._ws is None:
            raise BrowserCdpError("CDP WebSocket is not connected")
        try:
            import websocket  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise BrowserCdpError("websocket-client is unavailable") from exc
        deadline = time.monotonic() + max(0.0, duration)
        old_timeout = self._ws.gettimeout()
        self._ws.settimeout(min(0.25, max(0.05, duration or 0.05)))
        try:
            while time.monotonic() < deadline:
                try:
                    incoming = json.loads(self._ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as exc:
                    raise BrowserCdpError(f"Failed while collecting CDP events: {exc}") from exc
                if isinstance(incoming, dict) and isinstance(incoming.get("method"), str):
                    self._events.append(incoming)
        finally:
            self._ws.settimeout(old_timeout)
        events = self._events
        self._events = []
        return events

    def evaluate(self, expression: str, *, await_promise: bool = False) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
                "userGesture": True,
            },
        )
        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            exception = details.get("exception") if isinstance(details, dict) else None
            description = exception.get("description") if isinstance(exception, dict) else None
            text = details.get("text") if isinstance(details, dict) else None
            raise CdpProtocolError(description or text or f"JavaScript evaluation failed: {details}")
        remote = result.get("result", {})
        if not isinstance(remote, dict):
            return remote
        if "value" in remote:
            return remote["value"]
        if remote.get("type") == "undefined":
            return None
        return remote.get("description")


def require_browser(endpoint: str, *, timeout: float) -> dict[str, Any]:
    version = probe_version(endpoint, timeout=min(timeout, 2.0))
    if version is None:
        raise BrowserCdpError(
            f"Agent Chrome CDP is not reachable at {endpoint}. Run `ensure` or verify the adapter endpoint."
        )
    return version


def _powershell_executable() -> str | None:
    for name in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def launch_windows_agent_chrome(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.port != 9222:
        raise BrowserCdpError(
            "Automatic Chrome launch is only defined for the default local WSL adapter at http://localhost:9222"
        )
    powershell = _powershell_executable()
    if powershell is None:
        raise BrowserCdpError(
            "Cannot launch Windows Agent Chrome because powershell.exe/pwsh.exe is unavailable; start the persistent adapter manually"
        )
    command = r'''
$paths = @(
  (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
  (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
) | Where-Object { $_ -and (Test-Path $_) }
$chrome = $paths | Select-Object -First 1
if (-not $chrome) { throw 'Chrome executable not found in known Windows locations' }
$profile = Join-Path $env:USERPROFILE '.agent-browser\profile'
Start-Process -FilePath $chrome -ArgumentList @(
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=9222',
  "--user-data-dir=$profile",
  '--no-first-run',
  'about:blank'
)
Write-Output $chrome
'''.strip()
    try:
        completed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise BrowserCdpError(f"Failed to launch Windows Agent Chrome: {stderr.strip() or exc}") from exc
    return completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "chrome.exe"


def ensure_browser(endpoint: str, *, timeout: float) -> dict[str, Any]:
    version = probe_version(endpoint, timeout=min(timeout, 2.0))
    if version is not None:
        return {
            "connected": True,
            "reused": True,
            "endpoint": endpoint,
            "profileIdentity": PROFILE_IDENTITY,
            "browser": version.get("Browser"),
            "protocolVersion": version.get("Protocol-Version"),
        }
    executable = launch_windows_agent_chrome(endpoint)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        version = probe_version(endpoint, timeout=1.0)
        if version is not None:
            return {
                "connected": True,
                "reused": False,
                "endpoint": endpoint,
                "profileIdentity": PROFILE_IDENTITY,
                "executable": executable,
                "browser": version.get("Browser"),
                "protocolVersion": version.get("Protocol-Version"),
            }
        time.sleep(0.25)
    raise BrowserCdpError(f"Chrome was launched but CDP did not become reachable at {endpoint} within {timeout:g}s")


def ensure_then_targets(endpoint: str, *, timeout: float) -> list[dict[str, Any]]:
    if probe_version(endpoint, timeout=min(timeout, 1.5)) is None:
        ensure_browser(endpoint, timeout=timeout)
    return list_targets(endpoint, timeout=timeout)


def selected_target(endpoint: str, selector: str | None, *, timeout: float) -> dict[str, Any]:
    return select_target(ensure_then_targets(endpoint, timeout=timeout), selector)


def browser_client(version: dict[str, Any], *, timeout: float) -> CdpClient:
    ws = version.get("webSocketDebuggerUrl")
    if not isinstance(ws, str) or not ws:
        raise BrowserCdpError("CDP /json/version did not expose webSocketDebuggerUrl")
    return CdpClient(ws, timeout=timeout)


def page_client(target: dict[str, Any], *, timeout: float) -> CdpClient:
    ws = target.get("webSocketDebuggerUrl")
    if not isinstance(ws, str) or not ws:
        raise BrowserCdpError(f"Page target {target.get('id')} has no webSocketDebuggerUrl")
    return CdpClient(ws, timeout=timeout)


def wait_ready(client: CdpClient, *, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    last_state = ""
    while time.monotonic() < deadline:
        state = client.evaluate("document.readyState")
        last_state = str(state or "")
        if last_state == "complete":
            return last_state
        time.sleep(0.2)
    raise BrowserCdpError(f"Timed out waiting for document.readyState=complete; last state={last_state!r}")


def inspect_expression(text_limit: int, *, all_controls: bool = False) -> str:
    all_controls_js = "true" if all_controls else "false"
    return f"""
(() => {{
  const visible = (el) => {{
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  }};
  const bodyText = document.body?.innerText || '';
  const allControls = [...document.querySelectorAll('input, textarea, select, button, [contenteditable="true"]')].map((el, i) => {{
    const type = (el.type || '').toLowerCase();
    const identity = `${{el.id || ''}} ${{el.name || ''}}`.toLowerCase();
    const sensitiveName = /(password|passwd|token|secret|csrf|verification.?code|otp|authorization)/.test(identity) || /(^|[\\s_-])auth([\\s_-]|$)/.test(identity);
    const sensitive = type === 'password' || sensitiveName;
    return {{
    i,
    tag: el.tagName,
    type: el.type || '',
    id: el.id || '',
    name: el.name || '',
    value: sensitive ? '[redacted]' : (el.value ?? el.textContent ?? ''),
    placeholder: el.placeholder || '',
    readOnly: !!el.readOnly,
    checked: !!el.checked,
    multiple: !!el.multiple,
    accept: el.accept || '',
    disabled: !!el.disabled,
    visible: visible(el),
    ariaLabel: el.getAttribute('aria-label') || '',
    labels: el.labels ? [...el.labels].map(label => label.innerText.trim()).filter(Boolean).join(' | ') : '',
    text: (el.innerText || '').trim().slice(0, 300)
    }};
  }});
  const controls = {all_controls_js} ? allControls : allControls.filter(el =>
    el.type === 'file' || (el.visible && (el.tag !== 'BUTTON' || el.id || el.name || el.text || el.ariaLabel))
  );
  return {{
    title: document.title,
    href: location.href,
    readyState: document.readyState,
    bodyText: bodyText.slice(0, {int(text_limit)}),
    bodyTextLength: bodyText.length,
    bodyTextTruncated: bodyText.length > {int(text_limit)},
    controlCount: allControls.length,
    returnedControlCount: controls.length,
    controls
  }};
}})()
""".strip()


def interaction_point_expression(
    selector: str,
    *,
    allow_submit: bool = False,
    require_text_target: bool = False,
) -> str:
    selector_js = json.dumps(selector, ensure_ascii=False)
    allow_js = "true" if allow_submit else "false"
    require_text_js = "true" if require_text_target else "false"
    return f"""
(() => {{
  const selector = {selector_js};
  const el = document.querySelector(selector);
  if (!el) throw new Error(`No element matches ${{selector}}`);
  const tag = el.tagName.toLowerCase();
  const type = (el.type || '').toLowerCase();
  const submitLike = !!el.form && ((tag === 'button' && (type === '' || type === 'submit')) || (tag === 'input' && type === 'submit'));
  if (submitLike && !{allow_js}) {{
    throw new Error('Refusing submit-like click without --allow-submit');
  }}
  if (el.disabled) throw new Error('Refusing to interact with a disabled control');
  if ({require_text_js}) {{
    if (type === 'password') throw new Error('Password entry remains a human login boundary');
    const textInputTypes = new Set(['', 'text', 'search', 'email', 'tel', 'url', 'number']);
    const supported = (tag === 'input' && textInputTypes.has(type)) || tag === 'textarea' || el.isContentEditable;
    if (!supported) throw new Error(`type requires a text input, textarea, or contenteditable target; got ${{el.tagName}} type=${{type || '(none)'}}`);
    if (el.readOnly) throw new Error('Refusing to type into a readonly control; use its native UI');
  }}
  el.scrollIntoView({{block: 'center', inline: 'nearest'}});
  const rect = el.getBoundingClientRect();
  if (!(rect.width > 0 && rect.height > 0)) throw new Error('Target has no visible hit box');
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  const hit = document.elementFromPoint(x, y);
  if (!hit || !(hit === el || el.contains(hit))) {{
    const blocker = hit ? `${{hit.tagName}}#${{hit.id || ''}}.${{String(hit.className || '').replace(/\\s+/g, '.')}}` : 'none';
    throw new Error(`Target center is not pointer-reachable; elementFromPoint hit ${{blocker}}`);
  }}
  return {{
    x,
    y,
    tag: el.tagName,
    type: el.type || '',
    id: el.id || '',
    name: el.name || '',
    text: (el.innerText || el.value || '').trim().slice(0, 300),
    contenteditable: !!el.isContentEditable,
    href: location.href
  }};
}})()
""".strip()


def target_state_expression(selector: str) -> str:
    selector_js = json.dumps(selector, ensure_ascii=False)
    return f"""
(() => {{
  const selector = {selector_js};
  const el = document.querySelector(selector);
  if (!el) throw new Error(`No element matches ${{selector}}`);
  const active = document.activeElement;
  return {{
    tag: el.tagName,
    type: el.type || '',
    id: el.id || '',
    name: el.name || '',
    value: el.value ?? el.textContent ?? '',
    focused: active === el || (!!active && el.contains(active)),
    contenteditable: !!el.isContentEditable
  }};
}})()
""".strip()


def dispatch_primary_click(client: CdpClient, point: dict[str, Any]) -> None:
    x = point.get("x")
    y = point.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise CdpProtocolError(f"Interaction point is missing numeric coordinates: {point!r}")
    client.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
    client.call(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1},
    )
    client.call(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "buttons": 0, "clickCount": 1},
    )


def replace_focused_text(client: CdpClient, value: str) -> None:
    client.call(
        "Input.dispatchKeyEvent",
        {
            "type": "rawKeyDown",
            "key": "a",
            "code": "KeyA",
            "windowsVirtualKeyCode": 65,
            "nativeVirtualKeyCode": 65,
            "modifiers": 2,
            "commands": ["selectAll"],
        },
    )
    client.call(
        "Input.dispatchKeyEvent",
        {
            "type": "keyUp",
            "key": "a",
            "code": "KeyA",
            "windowsVirtualKeyCode": 65,
            "nativeVirtualKeyCode": 65,
            "modifiers": 2,
        },
    )
    client.call(
        "Input.dispatchKeyEvent",
        {
            "type": "rawKeyDown",
            "key": "Backspace",
            "code": "Backspace",
            "windowsVirtualKeyCode": 8,
            "nativeVirtualKeyCode": 8,
            "commands": ["deleteBackward"],
        },
    )
    client.call(
        "Input.dispatchKeyEvent",
        {
            "type": "keyUp",
            "key": "Backspace",
            "code": "Backspace",
            "windowsVirtualKeyCode": 8,
            "nativeVirtualKeyCode": 8,
        },
    )
    if value:
        client.call("Input.insertText", {"text": value})


def fill_expression(selector: str, value: str) -> str:
    selector_js = json.dumps(selector, ensure_ascii=False)
    value_js = json.dumps(value, ensure_ascii=False)
    return f"""
(() => {{
  const selector = {selector_js};
  const nextValue = {value_js};
  const el = document.querySelector(selector);
  if (!el) throw new Error(`No element matches ${{selector}}`);
  const tag = el.tagName.toLowerCase();
  const type = (el.type || '').toLowerCase();
  if (type === 'checkbox' || type === 'radio' || type === 'file' || type === 'password') {{
    throw new Error(`Use the dedicated interaction or human login boundary for input type ${{type}} instead of fill`);
  }}
  if (el.readOnly) throw new Error('Refusing to fill a readonly control; use its native UI or an explicitly justified eval');
  el.scrollIntoView({{block: 'center', inline: 'nearest'}});
  el.focus();
  if (tag === 'input') {{
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Native input value setter is unavailable');
    setter.call(el, nextValue);
  }} else if (tag === 'textarea') {{
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
    if (!setter) throw new Error('Native textarea value setter is unavailable');
    setter.call(el, nextValue);
  }} else if (tag === 'select') {{
    el.value = nextValue;
  }} else if (el.isContentEditable) {{
    throw new Error('Refusing DOM fill for contenteditable; use type so the editor receives real input events');
  }} else {{
    throw new Error(`Unsupported fill target: ${{el.tagName}}`);
  }}
  el.dispatchEvent(new Event('input', {{bubbles: true}}));
  el.dispatchEvent(new Event('change', {{bubbles: true}}));
  el.blur();
  return {{
    filled: true,
    tag: el.tagName,
    id: el.id || '',
    name: el.name || '',
    value: el.value ?? el.textContent ?? ''
  }};
}})()
""".strip()


def is_windows_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", value))


def running_in_wsl() -> bool:
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="ignore").casefold()
    except OSError:
        return False


def chrome_file_path(value: str) -> str:
    if is_windows_path(value):
        return value
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise BrowserCdpError(f"Upload file does not exist: {path}")
    if running_in_wsl():
        wslpath = shutil.which("wslpath")
        if not wslpath:
            raise BrowserCdpError("wslpath is unavailable; pass a Windows-accessible path explicitly")
        try:
            return subprocess.check_output([wslpath, "-w", str(path)], text=True, timeout=5).strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise BrowserCdpError(f"Failed to convert upload path for Windows Chrome: {path}") from exc
    return str(path)


def read_expression(value: str) -> str:
    if value == "-":
        expression = sys.stdin.read()
        if not expression.strip():
            raise BrowserCdpError("No JavaScript expression was provided on stdin")
        return expression
    return value


def read_json_object(value: str) -> dict[str, Any]:
    raw = sys.stdin.read() if value == "-" else value
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrowserCdpError(f"Invalid JSON parameters: {exc}") from exc
    if not isinstance(parsed, dict):
        raise BrowserCdpError("CDP call parameters must be a JSON object")
    return parsed


def response_header(headers: Any, name: str) -> str | None:
    if not isinstance(headers, dict):
        return None
    wanted = name.casefold()
    for key, value in headers.items():
        if str(key).casefold() == wanted:
            return str(value)
    return None


def summarize_network_events(events: Iterable[dict[str, Any]], *, url_contains: str | None = None) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    needle = url_contains.casefold() if url_contains else None
    for event in events:
        method = event.get("method")
        params = event.get("params")
        if not isinstance(params, dict):
            continue
        request_id = str(params.get("requestId", ""))
        if not request_id:
            continue
        if method == "Network.requestWillBeSent":
            request = params.get("request")
            if not isinstance(request, dict):
                continue
            url = str(request.get("url", ""))
            if needle and needle not in url.casefold():
                continue
            if request_id not in records:
                order.append(request_id)
                records[request_id] = {"requestId": request_id}
            records[request_id].update(
                {
                    "url": url,
                    "method": request.get("method"),
                    "resourceType": params.get("type"),
                }
            )
        elif method == "Network.responseReceived":
            response = params.get("response")
            if not isinstance(response, dict):
                continue
            url = str(response.get("url", ""))
            if needle and needle not in url.casefold():
                continue
            if request_id not in records:
                order.append(request_id)
                records[request_id] = {"requestId": request_id, "url": url}
            headers = response.get("headers")
            records[request_id].update(
                {
                    "url": url,
                    "resourceType": params.get("type") or records[request_id].get("resourceType"),
                    "status": response.get("status"),
                    "mimeType": response.get("mimeType"),
                    "contentType": response_header(headers, "content-type"),
                    "contentDisposition": response_header(headers, "content-disposition"),
                }
            )
    return [records[request_id] for request_id in order]
