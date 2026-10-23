# PowerShell | run-audit-v2.ps1 | Windows PowerShell 5.1+ | independent static audit, no game execution.
param([string]$Binary = 'E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe')
$ErrorActionPreference = 'Stop'
$pythonRuntime = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonRuntime) { $pythonRuntime = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $pythonRuntime) { throw 'Python 3.12+ was not found.' }
& $pythonRuntime -u (Join-Path $PSScriptRoot 'audit_v2.py') --binary $Binary --old (Join-Path $PSScriptRoot 'results') --out (Join-Path $PSScriptRoot 'audit-v2')
if ($LASTEXITCODE -ne 0) { throw "Audit failed: $LASTEXITCODE" }
& $pythonRuntime (Join-Path $PSScriptRoot 'curate_audit_v2.py') --binary $Binary --audit (Join-Path $PSScriptRoot 'audit-v2')
if ($LASTEXITCODE -ne 0) { throw "Evidence classification failed: $LASTEXITCODE" }
