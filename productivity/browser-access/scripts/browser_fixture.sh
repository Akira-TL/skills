#!/usr/bin/env bash
# Dedicated credential-free browser and HTTP fixture. Never connects to user profiles.
set -euo pipefail
browser_skill_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
browser_repo_dir="$(cd -- "$browser_skill_dir/../.." && pwd)"
browser_fixture_state="${BROWSER_FIXTURE_STATE:-/tmp/browser-access-fixture}"
mkdir -p "$browser_fixture_state" "$browser_repo_dir/logs"
case "${1:-}" in
  start)
    if [[ -f "$browser_fixture_state/chrome.pid" ]] && kill -0 "$(cat "$browser_fixture_state/chrome.pid")" 2>/dev/null; then exit 0; fi
    browser_fixture_chrome="${BROWSER_FIXTURE_CHROME:-/home/Akira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome}"
    [[ -x "$browser_fixture_chrome" ]] || { echo 'Set BROWSER_FIXTURE_CHROME to a local Chromium executable' >&2; exit 2; }
    UV_CACHE_DIR=/tmp/browser-hardening-uv uv run --no-project "$browser_skill_dir/tests/fixture_server.py" >"$browser_repo_dir/logs/browser-fixture-server.log" 2>&1 &
    echo "$!" > "$browser_fixture_state/server.pid"
    "$browser_fixture_chrome" --headless --no-sandbox --disable-gpu --remote-debugging-port=19322 --remote-debugging-address=127.0.0.1 --user-data-dir="$browser_fixture_state/profile" about:blank >"$browser_repo_dir/logs/browser-fixture-chrome.log" 2>&1 &
    echo "$!" > "$browser_fixture_state/chrome.pid"
    for browser_fixture_attempt in {1..50}; do
      if curl -fsS http://127.0.0.1:19322/json/version >/dev/null 2>&1 && curl -fsS http://127.0.0.1:19323/dynamic.html >/dev/null 2>&1; then exit 0; fi
      sleep 0.1
    done
    echo 'Local browser fixture failed to start; see logs/browser-fixture-*.log' >&2
    exit 2
    ;;
  stop)
    for browser_fixture_process in chrome server; do
      if [[ -f "$browser_fixture_state/$browser_fixture_process.pid" ]]; then
        kill "$(cat "$browser_fixture_state/$browser_fixture_process.pid")" 2>/dev/null || true
        rm -f "$browser_fixture_state/$browser_fixture_process.pid"
      fi
    done
    ;;
  *) echo 'Usage: browser_fixture.sh start|stop' >&2; exit 2 ;;
esac
