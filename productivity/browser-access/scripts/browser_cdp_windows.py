"""Read a Windows Chrome instance's identity without inspecting page content."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from browser_cdp_core import BrowserCdpError


@dataclass(frozen=True)
class WindowsChromeIdentity:
    executable: str
    user_data_dir: str
    profile_directory: str
    debugging_port: int
    browser_path: str


def powershell_executable() -> str:
    for name in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(name)
        if path:
            return path
    fallback = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    if fallback.is_file():
        return str(fallback)
    raise BrowserCdpError("Windows PowerShell is unavailable; cannot launch or verify local Windows Chrome")


def identity_command(port: int, *, timeout: float) -> str:
    if not 1 <= port <= 65535:
        raise BrowserCdpError("Invalid Windows CDP port")
    return r'''
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ChromeCommandLine {
    [DllImport("shell32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern IntPtr CommandLineToArgvW(string command, out int count);
    [DllImport("kernel32.dll")]
    static extern IntPtr LocalFree(IntPtr memory);
    public static string[] Split(string command) {
        int count;
        IntPtr memory = CommandLineToArgvW(command, out count);
        if (memory == IntPtr.Zero) throw new InvalidOperationException("Cannot parse Chrome command line");
        try {
            string[] result = new string[count];
            for (int index = 0; index < count; index++)
                result[index] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(memory, index * IntPtr.Size));
            return result;
        } finally { LocalFree(memory); }
    }
}
'@
function Read-ChromeSwitch([string[]] $arguments, [string] $name) {
    $values = @()
    for ($index = 1; $index -lt $arguments.Length; $index++) {
        $argument = $arguments[$index]
        if ($argument.StartsWith($name + '=', [StringComparison]::Ordinal)) {
            $values += $argument.Substring($name.Length + 1)
        } elseif ($argument -ceq $name) {
            if ($index + 1 -ge $arguments.Length) { throw 'Incomplete Chrome identity switch' }
            $values += $arguments[$index + 1]
        }
    }
    if ($values.Count -gt 1) { throw 'Duplicate Chrome identity switch' }
    if ($values.Count -eq 1) { return $values[0] }
    return ''
}
'''.strip() + f'''
$owners = @(Get-NetTCPConnection -State Listen -LocalPort {port} |
    Where-Object {{ $_.LocalAddress -in @('127.0.0.1', '::1', '0.0.0.0', '::') }} |
    Select-Object -ExpandProperty OwningProcess -Unique)
if ($owners.Count -ne 1) {{ throw 'CDP port has no unique Windows process owner' }}
$process = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $owners[0])
if (-not $process -or $process.Name -ine 'chrome.exe' -or -not $process.ExecutablePath -or -not $process.CommandLine) {{
    throw 'CDP port is not owned by an inspectable Windows Chrome process'
}}
$arguments = [ChromeCommandLine]::Split($process.CommandLine)
$directory = Read-ChromeSwitch $arguments '--user-data-dir'
$profileDirectory = Read-ChromeSwitch $arguments '--profile-directory'
$debuggingPort = Read-ChromeSwitch $arguments '--remote-debugging-port'
$version = Invoke-RestMethod -Uri 'http://localhost:{port}/json/version' -TimeoutSec {max(1, math.ceil(timeout))}
$browserPath = ([Uri] $version.webSocketDebuggerUrl).AbsolutePath
ConvertTo-Json -Compress -InputObject @(
    [string] $process.ExecutablePath, [string] $directory,
    [string] $profileDirectory, [string] $debuggingPort, [string] $browserPath
)
'''


def read_windows_identity(port: int, *, timeout: float) -> WindowsChromeIdentity:
    command = identity_command(port, timeout=timeout)
    try:
        completed = subprocess.run(
            [powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", command],
            check=True, capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        # Avoid returning the process command line or PowerShell HTTP diagnostics.
        raise BrowserCdpError("Cannot verify the local Windows Chrome process and CDP instance") from exc
    try:
        fields = json.loads(completed.stdout)
        if not isinstance(fields, list) or len(fields) != 5 or not all(isinstance(value, str) for value in fields):
            raise ValueError("Invalid identity fields")
        return WindowsChromeIdentity(fields[0], fields[1], fields[2], int(fields[3]), fields[4])
    except (ValueError, TypeError) as exc:
        raise BrowserCdpError("Windows Chrome did not return a complete verifiable identity") from exc
