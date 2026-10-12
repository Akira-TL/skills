param(
  [ValidateSet('start','stop')][string]$Action = 'start',
  [string]$LogPath
)
$ErrorActionPreference = 'Stop'
$fixtureProfile = Join-Path $env:TEMP 'browser-access-fixture-19324'
$fixturePidPath = Join-Path $env:TEMP 'browser-access-fixture-19324.pid'
if ($Action -eq 'stop') {
  if (Test-Path $fixturePidPath) {
    $fixturePid = [int](Get-Content $fixturePidPath)
    $fixtureProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$fixturePid"
    if ($fixtureProcess -and $fixtureProcess.CommandLine.Contains($fixtureProfile)) {
      Stop-Process -Id $fixturePid
    }
    Remove-Item $fixturePidPath
  }
  exit 0
}
$fixtureListener = Get-NetTCPConnection -LocalPort 19324 -State Listen -ErrorAction SilentlyContinue
if ($fixtureListener) { throw 'Port 19324 is occupied; stop the previous owned fixture before starting' }
$fixtureChrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path $fixtureChrome)) { throw 'Windows Chrome fixture executable is unavailable' }
$fixtureArguments = @('--headless', '--disable-gpu', '--enable-automation', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=19324', ('--user-data-dir="' + $fixtureProfile + '"'), 'about:blank')
$fixtureStarted = Start-Process $fixtureChrome -ArgumentList $fixtureArguments -RedirectStandardError $LogPath -RedirectStandardOutput ($LogPath + '.stdout') -PassThru
Set-Content -Path $fixturePidPath -Value $fixtureStarted.Id
