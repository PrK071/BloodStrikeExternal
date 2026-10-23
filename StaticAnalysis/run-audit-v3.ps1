# PowerShell | run-audit-v3.ps1 | Windows PowerShell 5.1+ | static PE evidence, no target execution.
param([string]$Binary = 'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
$ErrorActionPreference = 'Stop'
$pythonRuntime = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonRuntime) { $pythonRuntime = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $pythonRuntime) { throw 'Python 3.12+ was not found.' }
& $pythonRuntime -u (Join-Path $PSScriptRoot 'audit_v3.py') --binary $Binary
if ($LASTEXITCODE -ne 0) { throw "V3 extraction failed: $LASTEXITCODE" }
& $pythonRuntime (Join-Path $PSScriptRoot 'seal_audit_v3.py')
if ($LASTEXITCODE -ne 0) { throw "V3 report/integrity verification failed: $LASTEXITCODE" }
