# PowerShell | run-inspection.ps1 | PowerShell 7 / Windows x64 | Run the local build and access inspection.
param(
    [string]$InstallPath = 'E:\SteamLibrary\steamapps\common\BLOODSTRIKE',
    [string]$OffsetsPath = (Join-Path $PSScriptRoot 'StaticAnalysis\input\bloodstrike-offsets.json')
)
$ErrorActionPreference = 'Stop'
$taskPython = (Get-Command python -ErrorAction SilentlyContinue).Source
$taskPythonAlt = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $taskPython -and $taskPythonAlt) { $taskPython = $taskPythonAlt }
if (-not $taskPython) { throw 'Python was not found. Install Python 3.12 or newer.' }
$taskInspector = Join-Path $PSScriptRoot 'inspect_build.py'
$taskReport = Join-Path $PSScriptRoot ('reports\inspection-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
if (!(Test-Path -LiteralPath $taskPython)) { throw 'Bundled Python runtime was not found.' }
$taskGameProcesses = @(Get-Process -Name BloodStrike -ErrorAction SilentlyContinue)
if ($taskGameProcesses.Count -gt 1) { throw 'More than one game process exists. Select a PID explicitly with inspect_build.py.' }
$taskArguments = @($taskInspector, '--install', $InstallPath, '--offsets', $OffsetsPath, '--out', $taskReport)
if ($taskGameProcesses.Count -eq 1) { $taskArguments += @('--pid', [string]$taskGameProcesses[0].Id) }
& $taskPython @taskArguments
if ($LASTEXITCODE -ne 0) { throw "Inspection failed with exit code $LASTEXITCODE." }
Write-Output ('Report: ' + $taskReport)
