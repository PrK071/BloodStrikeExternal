# PowerShell / tools/run-menu.ps1 / PowerShell 7 Windows x64 / live game menu
param([string]$Python='C:/Users/luiz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
$ErrorActionPreference='Stop'
$runtimeRoot=Split-Path -Parent $PSScriptRoot
$gameMatches=@(Get-Process -Name BloodStrike | Where-Object {$_.MainWindowHandle -ne 0})
if($gameMatches.Count -ne 1){throw 'Expected one BloodStrike window.'}
& $Python (Join-Path $PSScriptRoot 'live_menu.py') --pid $gameMatches[0].Id --hwnd $gameMatches[0].MainWindowHandle --sample 'E:/SteamLibrary/steamapps/common/BLOODSTRIKE/Engine/Binaries/Win64/BloodStrike.exe'
exit $LASTEXITCODE
