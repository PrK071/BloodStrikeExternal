# PowerShell | run-static-analysis.ps1 | Windows PowerShell 5.1+ | Windows x64; files only.
param(
    [string]$Binary = 'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'results')
)
$ErrorActionPreference = 'Stop'
$pythonRuntime = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonRuntime) { $pythonRuntime = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $pythonRuntime) { throw 'Python 3.12+ was not found; install Python and the pinned requirements.' }
$offsetsPath = Join-Path $PSScriptRoot 'input\bloodstrike-offsets.json'
& $pythonRuntime -u (Join-Path $PSScriptRoot 'analyze_static.py') --binary $Binary --out $OutputDirectory --offsets $offsetsPath
if ($LASTEXITCODE -ne 0) { throw "Static analysis failed with exit code $LASTEXITCODE" }
& $pythonRuntime (Join-Path $PSScriptRoot 'verify_evidence.py') --binary $Binary --results $OutputDirectory
if ($LASTEXITCODE -ne 0) { throw "Evidence verification failed with exit code $LASTEXITCODE" }
