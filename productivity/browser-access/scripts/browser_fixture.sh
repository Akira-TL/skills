#!/usr/bin/env bash
# Dedicated credential-free fixture; never connects to daily browser profiles.
set -euo pipefail
browser_skill_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
browser_repo_dir="$(cd -- "$browser_skill_dir/../.." && pwd)"
browser_fixture_state="${BROWSER_FIXTURE_STATE:-/tmp/browser-access-fixture}"
browser_fixture_powershell="${BROWSER_FIXTURE_POWERSHELL:-/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe}"
mkdir -p "$browser_fixture_state" "$browser_repo_dir/logs"
case "${1:-}" in
  start|start-windows)
    browser_fixture_endpoint=http://127.0.0.1:19322
    if [[ "$1" == start-windows ]]; then browser_fixture_endpoint=http://127.0.0.1:19324; fi
    if [[ "$1" == start && -f "$browser_fixture_state/chrome.pid" ]] && kill -0 "$(cat "$browser_fixture_state/chrome.pid")" 2>/dev/null && curl -fsS http://127.0.0.1:19323/dynamic.html >/dev/null 2>&1; then exit 0; fi
    if ! curl -fsS http://127.0.0.1:19323/dynamic.html >/dev/null 2>&1; then
      UV_CACHE_DIR=/tmp/browser-hardening-uv uv run --no-project "$browser_skill_dir/tests/fixture_server.py" >"$browser_repo_dir/logs/browser-fixture-server.log" 2>&1 &
      echo "$!" > "$browser_fixture_state/server.pid"
    fi
    if [[ "$1" == start-windows ]]; then
      browser_fixture_windows_script="$(wslpath -w "$browser_skill_dir/scripts/browser_fixture_windows.ps1")"
      browser_fixture_windows_log="$(wslpath -w "$browser_repo_dir/logs/browser-fixture-windows.log")"
      "$browser_fixture_powershell" -NoProfile -ExecutionPolicy Bypass -File "$browser_fixture_windows_script" -Action start -LogPath "$browser_fixture_windows_log" >"$browser_repo_dir/logs/browser-fixture-windows-launch.log" 2>&1 &
      echo "$!" > "$browser_fixture_state/windows-launch.pid"
    else
      browser_fixture_chrome="${BROWSER_FIXTURE_CHROME:-}"
      if [[ -z "$browser_fixture_chrome" ]]; then
        for browser_fixture_candidate in chromium chromium-browser google-chrome; do
          if command -v "$browser_fixture_candidate" >/dev/null 2>&1; then browser_fixture_chrome="$(command -v "$browser_fixture_candidate")"; break; fi
        done
      fi
      if [[ -z "$browser_fixture_chrome" ]]; then
        for browser_fixture_candidate in "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux64/chrome; do
          if [[ -x "$browser_fixture_candidate" ]]; then browser_fixture_chrome="$browser_fixture_candidate"; fi
        done
      fi
      [[ -x "$browser_fixture_chrome" ]] || { echo 'Set BROWSER_FIXTURE_CHROME to a local Chromium executable' >&2; exit 2; }
      "$browser_fixture_chrome" --headless --no-sandbox --disable-gpu --disable-background-networking --no-first-run --remote-debugging-port=19322 --remote-debugging-address=127.0.0.1 --user-data-dir="$browser_fixture_state/profile" about:blank >"$browser_repo_dir/logs/browser-fixture-chrome.log" 2>&1 &
      echo "$!" > "$browser_fixture_state/chrome.pid"
    fi
    for browser_fixture_attempt in {1..100}; do
      if curl --max-time 1 -fsS "$browser_fixture_endpoint/json/version" >/dev/null 2>&1 && curl --max-time 1 -fsS http://127.0.0.1:19323/dynamic.html >/dev/null 2>&1; then exit 0; fi
      sleep 0.1
    done
    echo 'Local browser fixture failed to start; see logs/browser-fixture-*.log' >&2
    exit 2
    ;;
  stop-windows)
    "$browser_fixture_powershell" -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$browser_skill_dir/scripts/browser_fixture_windows.ps1")" -Action stop
    ;;
  stop)
    for browser_fixture_process in chrome server; do
      if [[ -f "$browser_fixture_state/$browser_fixture_process.pid" ]]; then
        browser_fixture_pid="$(cat "$browser_fixture_state/$browser_fixture_process.pid")"
        browser_fixture_command="$(tr '\0' ' ' <"/proc/$browser_fixture_pid/cmdline" 2>/dev/null || true)"
        if [[ "$browser_fixture_command" == *"$browser_fixture_state/profile"* || "$browser_fixture_command" == *"$browser_skill_dir/tests/fixture_server.py"* ]]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi
        rm -f "$browser_fixture_state/$browser_fixture_process.pid"
      fi
    done
    ;;
  *) echo 'Usage: browser_fixture.sh start|stop|start-windows|stop-windows' >&2; exit 2 ;;
esac
