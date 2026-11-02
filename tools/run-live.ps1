# PowerShell / tools/run-live.ps1 / PowerShell 7 Windows x64 / installed Blood Strike training build
[CmdletBinding()]
param(
    [string]$Python='C:/Users/luiz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
    [string]$Sample='E:/SteamLibrary/steamapps/common/BLOODSTRIKE/Engine/Binaries/Win64/BloodStrike.exe',
    [int]$Seconds=3600
)
$ErrorActionPreference='Stop'
$runtimeRoot=Split-Path -Parent $PSScriptRoot
$calibration=Get-Content -LiteralPath (Join-Path $runtimeRoot 'calibration.json') -Raw | ConvertFrom-Json
if($calibration.status -ne 'CALIBRATED'){throw 'Measured calibration is required.'}
$gameMatches=@(Get-Process -Name BloodStrike -ErrorAction Stop | Where-Object {$_.MainWindowHandle -ne 0})
if($gameMatches.Count -ne 1){throw 'Expected one BloodStrike game window.'}
$gameProcess=$gameMatches[0]
$gainX=([double]$calibration.counts_per_pixel[0]).ToString([Globalization.CultureInfo]::InvariantCulture)
$gainY=([double]$calibration.counts_per_pixel[1]).ToString([Globalization.CultureInfo]::InvariantCulture)
$measuredFov=([double]$calibration.field_of_view).ToString([Globalization.CultureInfo]::InvariantCulture)
Push-Location -LiteralPath $runtimeRoot
try {
    & $Python -m ExternalCore watch --pid $gameProcess.Id --hwnd $gameProcess.MainWindowHandle --sample $Sample --seconds $Seconds --fps 60 --show-overlay --allow-motion --max-age-ms 250 --aim --counts-per-pixel $gainX $gainY --calibration-fov $measuredFov --allow-unknown-visibility --aim-radius 500 --tau-ms 0 --max-step-counts 300 --target-local-y 1.55 --output (Join-Path $runtimeRoot 'live-session.json')
    exit $LASTEXITCODE
} finally {Pop-Location}
