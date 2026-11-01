# PowerShell | tools/run-tests.ps1 | PowerShell 7 / Windows x64 | project test suite.
[CmdletBinding()]
param([string]$Python = 'python', [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectRoot 'reports\tests' }
$testScript = Join-Path $PSScriptRoot 'run_tests.py'
& $Python $testScript --output-dir $OutputDirectory
exit $LASTEXITCODE
