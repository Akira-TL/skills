"""Exercise the generated launch command on Windows without opening Chrome."""
from __future__ import annotations

import base64
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_cdp_lifecycle as lifecycle


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


if __name__ == "__main__":
    unittest.main()
