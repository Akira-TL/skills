"""Exercise the generated launch command on Windows without opening Chrome."""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_cdp_lifecycle as lifecycle
import browser_cdp_windows as windows


def windows_powershell() -> str | None:
    executable = shutil.which("powershell.exe")
    fallback = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    return executable or (str(fallback) if fallback.is_file() else None)


@unittest.skipUnless(windows_powershell(), "Windows PowerShell is unavailable")
class WindowsLaunchTests(unittest.TestCase):
    def run_launch(self, *, occupied: bool) -> subprocess.CompletedProcess[str]:
        command = lifecycle.launch_command(lifecycle.BrowserConfig(
            endpoint="http://localhost:65530", user_data_dir=r"C:\Agent Launch Test",
            identity="launch-test",
        )).replace("65530", "$testPort")
        # Reserve a permitted ephemeral port in Windows itself, rather than WSL.
        script = r"""
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$ErrorActionPreference = 'Stop'
$v4 = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$v4.Server.ExclusiveAddressUse = $true
$v4.Start()
$testPort = $v4.LocalEndpoint.Port
$v6 = [Net.Sockets.TcpListener]::new([Net.IPAddress]::IPv6Loopback, $testPort)
$v6.Server.ExclusiveAddressUse = $true
$v6.Start()
function Start-Process { Write-Output 'TEST_CHROME_LAUNCH_REQUESTED' }
try {
"""
        if not occupied:
            script += "$v4.Stop(); $v6.Stop()\n"
        script += command + r"""
} finally { $v4.Stop(); $v6.Stop() }
"""
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return subprocess.run(
            [windows_powershell() or "powershell.exe", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=20,
        )

    def test_occupied_windows_port_is_rejected_before_launch(self) -> None:
        result = self.run_launch(occupied=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("TEST_CHROME_LAUNCH_REQUESTED", result.stdout)
        self.assertIn("CDP port", result.stderr)

    def test_bindable_windows_port_reaches_launch(self) -> None:
        result = self.run_launch(occupied=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TEST_CHROME_LAUNCH_REQUESTED", result.stdout)


@unittest.skipUnless(windows_powershell(), "Windows PowerShell is unavailable")
class WindowsIdentityCommandTests(unittest.TestCase):
    def inspect(self, command_line: str, *, owners: str = "31415") -> subprocess.CompletedProcess[str]:
        # Only OS discovery and HTTP are fixtures; Windows parses the real argv.
        fixture = f'''
function Get-NetTCPConnection {{
    foreach ($owner in @({owners})) {{
        [PSCustomObject] @{{ LocalAddress = '127.0.0.1'; OwningProcess = $owner }}
    }}
}}
function Get-CimInstance {{
    [PSCustomObject] @{{ Name = 'chrome.exe';
        ExecutablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
        CommandLine = {lifecycle.powershell_literal(command_line)} }}
}}
function Invoke-RestMethod {{
    [PSCustomObject] @{{ webSocketDebuggerUrl = 'ws://localhost:9333/devtools/browser/test-id' }}
}}
'''
        script = fixture + windows.identity_command(9333, timeout=10)
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return subprocess.run(
            [windows_powershell() or "powershell.exe", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", encoded],
            capture_output=True, text=True, timeout=20,
        )

    def test_quoted_directory_and_spaced_switch_are_read_without_automation(self) -> None:
        result = self.inspect(
            r'"C:\Program Files\Google\Chrome\Application\chrome.exe" '
            r'''"--user-data-dir=C:\Agent Data\O'Brien" --profile-directory "Profile 2" '''
            r'--remote-debugging-port=9333'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Agent Data\O'Brien", "Profile 2", "9333", "/devtools/browser/test-id",
        ])

    def test_duplicate_directory_is_rejected(self) -> None:
        result = self.inspect(
            r'chrome.exe --user-data-dir=C:\First --user-data-dir=C:\Second '
            r'--profile-directory=Default --remote-debugging-port=9333'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate Chrome identity switch", result.stderr)

    def test_multiple_process_owners_are_rejected(self) -> None:
        result = self.inspect("chrome.exe", owners="31415, 27182")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no unique Windows process owner", result.stderr)


if __name__ == "__main__":
    unittest.main()
