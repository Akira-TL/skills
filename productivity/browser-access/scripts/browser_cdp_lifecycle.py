"""Persistent dedicated Chrome selection and lifecycle for browser-access."""
from __future__ import annotations

import ntpath
import re
import shutil
import subprocess
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

from browser_cdp_core import (
    DEFAULT_ENDPOINT, PROFILE_IDENTITY, BrowserCdpError, browser_client,
    list_targets, probe_version, select_target,
)


@dataclass(frozen=True)
class BrowserConfig:
    endpoint: str = DEFAULT_ENDPOINT
    user_data_dir: str | None = None
    profile_directory: str = "Default"
    identity: str | None = PROFILE_IDENTITY


def normalized_directory(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(value))


def validate_config(config: BrowserConfig) -> None:
    try:
        parsed = urllib.parse.urlsplit(config.endpoint)
        port = parsed.port
    except ValueError as exc:
        raise BrowserCdpError(f"Invalid CDP endpoint: {config.endpoint}") from exc
    if (re.search(r"[\x00-\x20]", config.endpoint) or
            parsed.scheme not in {"http", "https"} or not parsed.hostname or
            parsed.username or parsed.password or parsed.path not in {"", "/"} or
            parsed.query or parsed.fragment or port == 0):
        raise BrowserCdpError("CDP endpoint must be an HTTP(S) origin without credentials, path, query or fragment")
    if (not config.profile_directory or config.profile_directory in {".", ".."} or
            re.search(r'[\\/\x00-\x1f\"<>:|?*]', config.profile_directory) or
            config.profile_directory.endswith((".", " "))):
        raise BrowserCdpError("--profile-directory must be a single Chrome profile directory name")
    if config.user_data_dir is None:
        if config.profile_directory != "Default":
            raise BrowserCdpError("A custom --profile-directory requires a dedicated --user-data-dir")
        return
    path = config.user_data_dir
    if not re.match(r"^[A-Za-z]:[\\/]", path) or re.search(r'[\x00-\x1f\"]', path):
        raise BrowserCdpError("--user-data-dir must be an absolute Windows path without control characters or double quotes")
    normalized = normalized_directory(path)
    _, tail = ntpath.splitdrive(normalized)
    components = tail.strip("\\").split("\\")
    if tail == "\\" or any(part.endswith((".", " ")) or re.search(r'[<>:|?*]', part) for part in components):
        raise BrowserCdpError("--user-data-dir must be a dedicated directory with valid Windows path components")
    if re.search(r"\\google\\chrome\\user data(?:\\|$)", normalized):
        raise BrowserCdpError("Daily Chrome data directories are outside browser-access's dedicated configuration scope")
    if re.search(r"\\\.agent-browser\\profile(?:\\|$)", normalized):
        raise BrowserCdpError("The default Agent directory is reserved; omit configuration options to use agent-browser")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"} and port == 9222:
        raise BrowserCdpError("Port 9222 is reserved for agent-browser; use a separate port for a dedicated configuration")


def config_from_options(endpoint: str | None, user_data_dir: str | None,
                        profile_directory: str | None) -> BrowserConfig:
    if user_data_dir is not None and endpoint is None:
        raise BrowserCdpError("A custom --user-data-dir requires an explicit independent --endpoint")
    config = BrowserConfig(
        endpoint=endpoint if endpoint is not None else DEFAULT_ENDPOINT,
        user_data_dir=user_data_dir,
        profile_directory=profile_directory if profile_directory is not None else "Default",
        identity=ntpath.basename(ntpath.normpath(user_data_dir)) if user_data_dir else
                 (PROFILE_IDENTITY if endpoint is None or endpoint.rstrip("/") == DEFAULT_ENDPOINT else None),
    )
    validate_config(config)
    return config


def _powershell_executable() -> str:
    for name in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(name)
        if path:
            return path
    raise BrowserCdpError("Windows PowerShell is unavailable; start the dedicated Chrome adapter manually")


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def launch_command(config: BrowserConfig) -> str:
    validate_config(config)
    parsed = urllib.parse.urlsplit(config.endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"} or not parsed.port:
        raise BrowserCdpError("Automatic Chrome launch requires a local HTTP endpoint with an explicit port")
    if config.user_data_dir is None and parsed.port != 9222:
        raise BrowserCdpError("Automatic launch on another port requires a dedicated --user-data-dir")
    directory = powershell_literal(config.user_data_dir) if config.user_data_dir else \
        "(Join-Path $env:USERPROFILE '.agent-browser\\profile')"
    return r'''
$ErrorActionPreference = 'Stop'
$paths = @(
  (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
  (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
) | Where-Object { $_ -and (Test-Path $_) }
$chrome = $paths | Select-Object -First 1
if (-not $chrome) { throw 'Chrome executable not found in known Windows locations' }
'''.strip() + f'''
$profile = [IO.Path]::GetFullPath({directory}).TrimEnd('\\')
$daily = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Google\\Chrome\\User Data'))
if ($profile.TrimEnd('\\') -ieq $daily.TrimEnd('\\') -or $profile.StartsWith($daily.TrimEnd('\\') + '\\', [StringComparison]::OrdinalIgnoreCase)) {{
  throw 'Daily Chrome data directories are outside the dedicated adapter scope'
}}
Start-Process -FilePath $chrome -ArgumentList @(
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port={parsed.port}',
  ('"--user-data-dir=' + $profile + '"'),
  {powershell_literal('"--profile-directory=' + config.profile_directory + '"')},
  '--enable-automation',
  '--no-first-run',
  'about:blank'
)
Write-Output $chrome
'''


def launch_windows_agent_chrome(config: BrowserConfig) -> str:
    command = launch_command(config)
    try:
        completed = subprocess.run(
            [_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", command],
            check=True, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise BrowserCdpError(f"Failed to launch dedicated Chrome: {stderr.strip() or exc}") from exc
    return completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "chrome.exe"


def verify_profile(config: BrowserConfig, version: dict[str, Any], *, timeout: float) -> bool:
    if config.user_data_dir is None:
        return False  # Preserve existing endpoint-only/default connections without claiming verified identity.
    try:
        with browser_client(version, timeout=timeout) as client:
            arguments = client.call("Browser.getBrowserCommandLine").get("arguments", [])
    except BrowserCdpError as exc:
        raise BrowserCdpError(
            "Cannot verify the selected dedicated profile. Start that instance with --enable-automation; "
            "the CLI will not replace or close an existing browser."
        ) from exc
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise BrowserCdpError("Browser did not return valid command-line arguments for profile verification")
    def switch(name: str) -> str | None:
        for index, item in enumerate(arguments):
            if item.startswith(name + "="):
                return item[len(name) + 1:].strip('"')
            if item == name and index + 1 < len(arguments):
                return arguments[index + 1].strip('"')
        return None
    directory = switch("--user-data-dir")
    profile = switch("--profile-directory")
    if directory is None or normalized_directory(directory) != normalized_directory(config.user_data_dir) or profile != config.profile_directory:
        raise BrowserCdpError("The CDP endpoint belongs to a different or unverifiable Chrome profile; refusing to control it")
    return True


def browser_status(config: BrowserConfig, *, timeout: float) -> dict[str, Any]:
    validate_config(config)
    version = probe_version(config.endpoint, timeout=min(timeout, 2.0))
    result: dict[str, Any] = {
        "connected": version is not None, "endpoint": config.endpoint,
        "profileIdentity": config.identity, "userDataDir": config.user_data_dir,
        "profileDirectory": config.profile_directory, "profileVerified": False,
        "browser": version.get("Browser") if version else None,
        "protocolVersion": version.get("Protocol-Version") if version else None,
    }
    if version is not None:
        try:
            result["profileVerified"] = verify_profile(config, version, timeout=timeout)
        except BrowserCdpError as exc:
            result["profileError"] = str(exc)
    return result


def ensure_browser(config: BrowserConfig, *, timeout: float) -> dict[str, Any]:
    validate_config(config)
    version = probe_version(config.endpoint, timeout=min(timeout, 2.0))
    reused = version is not None
    executable = None
    if version is None:
        executable = launch_windows_agent_chrome(config)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            version = probe_version(config.endpoint, timeout=1.0)
            if version is not None:
                break
            time.sleep(0.25)
    if version is None:
        raise BrowserCdpError(f"Chrome was launched but CDP did not become reachable at {config.endpoint} within {timeout:g}s")
    verified = verify_profile(config, version, timeout=timeout)
    return {
        "connected": True, "reused": reused, "endpoint": config.endpoint,
        "profileIdentity": config.identity, "userDataDir": config.user_data_dir,
        "profileDirectory": config.profile_directory, "profileVerified": verified,
        "executable": executable, "browser": version.get("Browser"),
        "protocolVersion": version.get("Protocol-Version"),
    }


def ensure_then_targets(config: BrowserConfig, *, timeout: float) -> list[dict[str, Any]]:
    ensure_browser(config, timeout=timeout)
    return list_targets(config.endpoint, timeout=timeout)


def selected_target(config: BrowserConfig, selector: str | None, *, timeout: float) -> dict[str, Any]:
    return select_target(ensure_then_targets(config, timeout=timeout), selector)
